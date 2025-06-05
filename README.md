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
4.  Check the lambda function is working or not using `curl` command from terminal
