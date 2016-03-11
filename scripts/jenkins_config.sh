#!/bin/bash

get_artifact_url() {
    URL_BASE=$(curl --silent $JENKINS_URL/job/Mesos/job/$1/api/json | python -c 'import sys, json; js = json.load(sys.stdin); print js["lastStableBuild"]["url"]')
    URL_RUN0=$(curl --silent $URL_BASE/api/json | python -c 'import sys, json; js = json.load(sys.stdin); print js["runs"][0]["url"]')
    echo $(curl --silent $URL_RUN0/api/json | python -c 'import sys, json; js = json.load(sys.stdin); print js["url"] + "artifact/" + js["artifacts"][0]["relativePath"]')
}


RME=$(get_artifact_url riak-mesos-executor)
RMS=$(get_artifact_url riak-mesos-scheduler)
RMD=$(get_artifact_url riak-mesos-director)
RE=$(get_artifact_url riak_explorer)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TOOLS_TEMPLATE=$DIR/../config/config.template.json
TOOLS_REMOTE=$DIR/../config/config.jenkins.json

cp $TOOLS_TEMPLATE $TOOLS_REMOTE
sed -i "s,{{executor_url}},$RME,g" $TOOLS_REMOTE
sed -i "s,{{scheduler_url}},$RMS,g" $TOOLS_REMOTE
sed -i "s,{{proxy_url}},$RMD,g" $TOOLS_REMOTE
sed -i "s,{{explorer_url}},$RE,g" $TOOLS_REMOTE
# sed -i "s,{{node_url}},$RMS,g" $TOOLS_REMOTE
