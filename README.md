## cdk-s3-cloudfront

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

This [AWS CDK Python code](s3_cloudfront/s3_cloudfront_stack.py) can be used to deploy a CloudFront distribution pointing to an S3 Bucket, with an associated SSL Certificate, as well as an IAM user account with permissions to manage files in the S3 bucket.

If you don't like using the CDK directly, you can just use the generated [CloudFormation.yaml](CloudFormation.yaml) file to deploy the CloudFormation stack.


For additional details, see [CloudFront and S3 Bucket CloudFormation Stack](https://technotes.videre.us/en/cloud/cloudfront-and-s3-bucket-cloudformation-stack/).



# Build

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .env
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .env/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth --path-metadata false --version-reporting false > CloudFormation.yaml
```

# Deploy

Deploy the `CloudFormation.yaml` template in your AWS account.

# Notes

A few notes about this deployment:
- This stack assumes that you have a valid DNS Domain Name that you can use.
- The SSL Certificate will be created by AWS and uses DNS Validation to verify ownership of the DNS name. The Stack will *not* complete the deployment until the DNS validation has been completed.
- For safety, the S3 bucket removal Policy is set to RETAIN, the bucket and objects will *not* be deleted if you remove the CloudFormation stack.
- The `aws_secret_access_key` for the IAM User account that is created will be stored in AWS Secrets Manager. Retrieve the value and delete the secret if you don't want to keep being charged for it.
- Two S3 Bucket Lifecycle Policies will be created, one to delete incomplete multipart uploads (highly recommended for all your buckets), and one to move objects to the `INTELLIGENT_TIERING` Storage Class.
