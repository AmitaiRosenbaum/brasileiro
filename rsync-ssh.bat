rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '.venv' --exclude 'pdf-processing-engine' \
-e "ssh -i ~/.ssh/brasileiro-amitai.pem" \
. ubuntu@ec2-3-106-221-56.ap-southeast-2.compute.amazonaws.com:~/app