REMOTE="aliyun"
DIR="fq-config-server"

# ssh $REMOTE "cd $DIR && git pull"
scp config.yml $REMOTE:$DIR/
