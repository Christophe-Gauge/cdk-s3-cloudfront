from constructs import Construct
from aws_cdk import (
    aws_iam as iam,
    aws_certificatemanager as cm,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_secretsmanager as secretsmanager,
    Stack, Tags, aws_s3, RemovalPolicy, Duration, CfnOutput, CfnParameter
)


class S3CloudfrontStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        site_domain_name = CfnParameter(self,
                                        id='domain_name',
                                        description="Domain Name",
                                        default="static.example.com",
                                        type="String",
                                              ).value_as_string
        
        source_ip = CfnParameter(self,
                                        id='source_ip',
                                        description="Source IP Address",
                                        default="***.***.***.***",
                                        type="String",
                                      ).value_as_string
        
        stack_name = self.stack_name
        Tags.of(self).add('Project', "Wagtail Images");
        Tags.of(self).add('stackName', stack_name);
        Tags.of(self).add('Domain', site_domain_name);

        txt_domain_name = site_domain_name.replace('.', '_')

        myBucket = aws_s3.Bucket(
            self,
            's3_bucket',
            bucket_name = site_domain_name,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            access_control=aws_s3.BucketAccessControl.PRIVATE,
            public_read_access=False,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            # removal_policy=RemovalPolicy.DESTROY,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            lifecycle_rules = [
                aws_s3.LifecycleRule(
                    id="multipart",
                    enabled=True,
                    abort_incomplete_multipart_upload_after=Duration.days(1),
                    expired_object_delete_marker=True,
                ),
                aws_s3.LifecycleRule(
                    id="IA",
                    enabled=True,
                    transitions=[{
                        "storageClass": aws_s3.StorageClass.INTELLIGENT_TIERING,
                        "transitionAfter": Duration.days(0)
                    }]
                )
             ]
        )

        user = iam.User(self, "User")
        access_key = iam.AccessKey(self, "AccessKey", user=user)
        secret = secretsmanager.Secret(self, "Secret",
            secret_string_value=access_key.secret_access_key
        )

        policy = iam.Policy(self, 'myPolicy', statements=[iam.PolicyStatement(
            resources=[user.user_arn],
            actions=["iam:ListAccessKeys",
                "iam:CreateAccessKey",
                "iam:DeleteAccessKey"
            ]
          )]
        )
        policy.attach_to_user(user)


        
        myBucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowUserManageBucket",
                effect=iam.Effect.ALLOW,
                actions=["s3:ListBucket",
                        "s3:GetBucketLocation",
                        "s3:ListBucketMultipartUploads",
                        "s3:ListBucketVersions"],
                resources=[myBucket.bucket_arn],
                principals=[iam.ArnPrincipal(user.user_arn)],
            )
        )

        myBucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowUserManageBucketObjects",
                effect=iam.Effect.ALLOW,
                actions=["s3:*Object"],
                resources=[myBucket.arn_for_objects("*")],
                principals=[iam.ArnPrincipal(user.user_arn)],
            )
        )

        myBucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="RestrictByIPAddress",
                effect=iam.Effect.DENY,
                actions=["s3:*Object"],
                resources=[myBucket.bucket_arn,myBucket.arn_for_objects("*")],
                principals=[iam.AnyPrincipal()],
                conditions = {
                  'NotIpAddress' : {
                    'aws:SourceIp' : source_ip
                  }
                }
            )
        )

        certificate = cm.Certificate(self, "MyCertificate",
          domain_name=site_domain_name,
          certificate_name=site_domain_name,
          validation=cm.CertificateValidation.from_dns()
        )

        distribution = cloudfront.Distribution(
            self,
            "cloudfront_distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(myBucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            domain_names=[site_domain_name],
            certificate=certificate,
            default_root_object="index.html",
        )

        # Add stack outputs
        CfnOutput(
            self,
            "userNAME",
            value=user.user_name,
        )
        CfnOutput(
            self,
            "accessKeyId",
            value=access_key.to_string(),
        )
        CfnOutput(
            self,
            "SiteBucketName",
            value=myBucket.bucket_name,
        )
        CfnOutput(
            self,
            "DistributionId",
            value=distribution.distribution_id,
        )
        CfnOutput(
            self,
            "CertificateArn",
            value=certificate.certificate_arn,
        )