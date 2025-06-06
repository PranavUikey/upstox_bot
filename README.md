### Upstox_Bot Nifty50 Options Trading Bot


#### AWS Steps:

1. Amazon AWS SES (Verified Sender and Reciever of Authentication Email).
2. Go to Amazon AWS Systems Manager Add/Parameter Store add parameters(e.g.access_token,client_id,client_secret,redirect_uri)
3. Create 2 Amazon AWS Lambda Functions
  a. SendEmailFunction (To send user authentication Email).
    i.Create 2 environment variables CLIENT_ID & REDIRECT_URI: 
  b. ExtractAuthCode (To extract auth code from url and exchange auth code with auth token).
    i. Upload code from zip file (`pip` can't be used for installing Python package, install the package locally, zip it and upload it)
       - pip install -t . requests
       - zip -r lambda_package.zip .
4. Create Roles and policies for each Lambda functions and one extra for Amazon Email Services.
5. Check the lambda function is working or not using `curl` command from terminal and make sure SSM contains now access_token in parameter store.
6. Now Create an EC2 Instane Ubuntu(t2.micro) with assigned role and policy to access SSM parameters.
7. Create an venv named `upstox_env` in instance, 
