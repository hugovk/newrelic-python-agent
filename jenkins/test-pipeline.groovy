import groovy.json.JsonSlurper
import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testSuffix = "__docker-test"
String slackChannel = '#python-agent'


def jsonSlurper = new JsonSlurper()
def packnsendTests = jsonSlurper.parseText(readFileFromWorkspace(
    './jenkins/test-pipeline-config.json')).packnsendTests


use(extensions) {
    view('PY_Tests', 'Test jobs',
         "(_PYTHON-AGENT-DOCKER-TESTS_)|(.*${testSuffix})|(oldstyle.*)")

    multiJob('_PYTHON-AGENT-DOCKER-TESTS_') {
        description('Perform full suite of tests on Python Agent')
        logRotator { numToKeep(10) }
        triggers { cron('H 10 * * *') }
        label('ec2-linux')
        publishers {
            extendedEmail('python-agent-dev@newrelic.com')
        }

        parameters {
            stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                        'Branch in git repository to run test against.')
            stringParam('AGENT_FAKE_COLLECTOR', 'false',
                        'Whether fake collector is used or not.')
            stringParam('AGENT_PROXY_HOST', '',
                        'URI for location of proxy. e.g. http://proxy_host:proxy_port')
        }

        steps {
            packnsendTests.each { phaseName, tests ->
                phase(phaseName, 'COMPLETED') {
                    for (test in tests) {
                        job("${test.name}${testSuffix}") {
                            killPhaseCondition('NEVER')
                        }
                    }
                }
            }
        }

        slack(slackChannel){
            notifySuccess true
        }
    }

    // create all packnsend base tests
    packnsendTests.each { phaseName, tests ->
        tests.each { test ->
            baseJob("${test.name}${testSuffix}") {
                label('ec2-linux')
                repo(repoFull)
                branch('${GIT_REPOSITORY_BRANCH}')

                configure {
                    blockOnJobs('.*-Reset-Nodes')
                    description(test.description)
                    logRotator { numToKeep(10) }
                    if (test.disabled == "true") {
                        println "    Disabling test ${test.name}"
                        disabled()
                    }

                    parameters {
                        stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                                    'Branch in git repository to run test against.')
                        stringParam('AGENT_FAKE_COLLECTOR', 'true',
                                    'Whether fake collector is used or not.')
                        stringParam('AGENT_PROXY_HOST', '',
                                    'URI for location of proxy. e.g. http://proxy_host:proxy_port')
                    }

                    steps {
                        environmentVariables {
                            env('NEW_RELIC_DEVELOPER_MODE', '${AGENT_FAKE_COLLECTOR}')
                            env('NEW_RELIC_PROXY_HOST', '${AGENT_PROXY_HOST}')
                            // dogestry creds
                            env('AWS_ACCESS_KEY_ID', '${NR_DOCKER_DEV_ACCESS_KEY_ID}')
                            env('AWS_SECRET_ACCESS_KEY', '${NR_DOCKER_DEV_SECRET_ACCESS_KEY}')
                            env('DOCKER_HOST', 'unix:///var/run/docker.sock')
                        }
                        shell('./jenkins/prep_node_for_test.sh')
                        for (testCmd in test.commands) {
                            shell(testCmd)
                        }
                    }
                }
            }
        }
    }

    ['develop', 'master', 'pullrequest'].each { jobType ->
        jaasBaseJob("oldstyle-tests-${jobType}") {
            label('ec2-linux')
            description('Run the old style tests (i.e. ./tests.sh)')
            logRotator { numToKeep(10) }
            blockOnJobs('.*-Reset-Nodes')

            if (jobType == 'pullrequest') {
                repositoryPR(repoFull)
                triggers {
                    // run for all pull requests
                    pullRequest {
                        permitAll(true)
                        useGitHubHooks()
                    }
                }
            }
            else {
                repository(repoFull, jobType)
                triggers {
                    // trigger on push to develop/master
                    githubPush()
                }
            }

            steps {
                environmentVariables {
                    // dogestry creds
                    env('AWS_ACCESS_KEY_ID', '${NR_DOCKER_DEV_ACCESS_KEY_ID}')
                    env('AWS_SECRET_ACCESS_KEY', '${NR_DOCKER_DEV_SECRET_ACCESS_KEY}')
                    env('DOCKER_HOST', 'unix:///var/run/docker.sock')
                }
                shell('./jenkins/prep_node_for_test.sh')
                shell('./build.sh')
                shell('./docker/packnsend run /data/tests.sh')
            }

            slackQuiet(slackChannel) {
                notifySuccess true
            }
        }
    }
}
