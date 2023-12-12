import typing as t
from constructs import Construct
from aws_cdk import (
    aws_iam as iam,
    aws_certificatemanager as cm,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_secretsmanager as secretsmanager,
    Stack, Tags, aws_s3, RemovalPolicy, Duration, CfnOutput, CfnParameter, Aws
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

        certificate = cm.Certificate(self, "MyCertificate",
          domain_name=site_domain_name,
          certificate_name=site_domain_name,
          validation=cm.CertificateValidation.from_dns()
        )

        cfn_origin_access_control = cloudfront.CfnOriginAccessControl(self, "MyCfnOriginAccessControl",
            origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name=site_domain_name,
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4",

                # the properties below are optional
                description="CF S3 Origin Access Control"
            )
        )

        distribution = cloudfront.Distribution(
            self, "CloudFrontDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                compress=True,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                origin_request_policy=cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                origin=origins.S3Origin(
                    myBucket, origin_id='s3-static-frontend',
                )
            ),
            domain_names=[site_domain_name],
            certificate=certificate,
            http_version=cloudfront.HttpVersion.HTTP2,
            enabled=True,
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404, response_page_path="/index.html", response_http_status=200,
                    ttl=Duration.seconds(60)),
            ]
        )

        # Override the default behavior to use OAC and not OAI
        # Because CDK does not have full support for this feature yet
        # Based on: https://github.com/aws/aws-cdk/issues/21771#issuecomment-1282780627
        cf_cfn_distrib = t.cast(
            cloudfront.CfnDistribution,
            distribution.node.default_child,
        )
        cf_cfn_distrib.add_property_override(
            'DistributionConfig.Origins.0.OriginAccessControlId',
            cfn_origin_access_control.get_att('Id'),
        )
        cf_cfn_distrib.add_property_override(
            'DistributionConfig.Origins.0.S3OriginConfig.OriginAccessIdentity',
            '',
        )

        myBucket.add_to_resource_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['s3:GetObject', 's3:ListBucket'],
            resources=[f'{myBucket.bucket_arn}/*', myBucket.bucket_arn],
            principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
            conditions={
                "StringEquals": {
                    "aws:SourceArn": f"arn:aws:cloudfront::{Aws.ACCOUNT_ID}:distribution/{distribution.distribution_id}"
                }
            }
        ))

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
            "distributionDomainName",
            value=distribution.distribution_domain_name,
        )
        CfnOutput(
            self,
            "CertificateArn",
            value=certificate.certificate_arn,
        )