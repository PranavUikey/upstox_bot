### Upstox_Bot Nifty50 Options Trading Bot


#### AWS Steps:

1. Amazon AWS SES (Verified Sender and Reciever of Authentication Email).
2. Go to Amazon AWS Systems Manager Add/Parameter Store add parameters(e.g.access_token,client_id,client_secret,redirect_uri)
3. Create 2 Amazon AWS Lambda Functions

  a. SendEmailFunction (To send user authentication Email).

    i.Create 2 environment variables CLIENT_ID & REDIRECT_URI: 

  b. ExtractAuthCode (To extract auth code from url and exchange auth code with auth token).

    i. Upload code from zip file (`pip` can't be used for installing Python package, install the package locally, zip it and upload it)

    ```{bash}
      >>> pip install -t . requests
      >>> zip -r lambda_package.zip .
    ```
4. Create Roles and policies for each Lambda functions and one extra for Amazon Email Services.
5. Check the lambda function is working or not using `curl` command from terminal and make sure SSM contains now access_token in parameter store.
6. Now Create an EC2 Instane Ubuntu(t2.micro) with assigned role and policy to access SSM parameters.
7. Create and activate venv named `upstox_env` in instance, `source upstox_env/bin/activate`.
8. Connect Github with EC2 instance using Github Actions. 
  
  **Step 1: Generate SSH Key Pair**
  
    Run Following commands on your local machine:
    
    ```{bash}
      >>> ssh-keygen -t rsa -b 4096 -f ~/.ssh/github-actions-ec2 -C "github-actions-deploy"
    ``` 

    When prompted:

    - Press Enter to skip passphrase.

    - This creates two files:

    - Private key: ~/.ssh/github-actions-ec2

    - Public key: ~/.ssh/github-actions-ec2.pub

    ```{bash}
      >>> cat ~/.ssh/github-actions-ec2
    ```

    - Copy the entire key output (starts with -----BEGIN OPENSSH PRIVATE KEY-----).

    - Go to your GitHub repo → Settings → Secrets → Actions → New repository secret:

    - Name: EC2_SSH_KEY

    - Value: (Paste the private key content)
  
  **Step 2: Add Public Key to EC2**
    SSH into your EC2 instance

    ```{bash}
      >>> ssh -i your_existing_key.pem ubuntu@<EC2_PUBLIC_IP>    
    ```

    Once inside the EC2 instance, run:
    ```{bash}
      >>> mkdir -p ~/.ssh
      >>> nano ~/.ssh/authorized_keys
    ```
    Copy the contents of `github-actions-ec2.pub` from your local system and paste it in `authorized_keys`. Save and exit.
    (Ctrl + O, Ctrl X)

    Set correct permissions:
    ```{bash}
      >>> chmod 700 ~/.ssh
      >>> chmod 600 ~/.ssh/authorized_keys
    ```

  **Step 3: Add EC2 User and Host Secrets**

    `EC2_USER`: Usually ubuntu for Ubuntu AMIs.

    `EC2_HOST`: Your EC2 public IP (e.g., 13.233.45.123)