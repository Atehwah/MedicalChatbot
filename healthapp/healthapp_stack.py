from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb
)
from constructs import Construct
from aws_cdk.aws_lambda_event_sources import S3EventSource

from cdklabs.generative_ai_cdk_constructs import (
    bedrock
)

class HealthappStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        table = dynamodb.Table(
            self,
            "HealthTable",
            table_name="heath-table",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        kb = bedrock.KnowledgeBase(self, 'HealthKnowledgeBase', 
            embeddings_model= bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V1,                  
        )

        kbArn = f'arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:knowledge-base/{kb.knowledge_base_id}'
        
        documentBucket = s3.Bucket(
            self, 
            'HealthDocumentBucket',
            removal_policy=RemovalPolicy.DESTROY,
                                   
        )
        

        documentDatasource = bedrock.S3DataSource(self, 'KBS3DataSource',
            bucket= documentBucket,
            knowledge_base=kb,
            data_source_name='documents',
            chunking_strategy= bedrock.ChunkingStrategy.FIXED_SIZE,
            max_tokens=500,
            overlap_percentage=20   
        )

        self.kbQueryLambdaFunction = _lambda.Function(
            self, 'KBQueryFunction',
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset('lambda'),
            handler='app.handler',
            environment={
                'KB_ID': kb.knowledge_base_id,
                'KB_MODEL_ARN': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0',
                'TABLE_NAME': table.table_name
            },
            timeout=Duration.minutes(15),
        )
        
        # Lambda injestion rrole
        lambda_ingestion_policy = iam.PolicyStatement(
                            actions=["bedrock:StartIngestionJob"],
                            resources=[kb.knowledge_base_arn],
                        )
        # Define the Injestion Lambda function
        lambda_ingestion_job = _lambda.Function(
            self,
            "IngestionJob",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset('lambda'),
            handler='sync_bedrock.handler',
            timeout=Duration.minutes(15),
            environment={
                "KNOWLEDGE_BASE_ID": kb.knowledge_base_id,
                "DATA_SOURCE_ID": documentDatasource.data_source_id
            }
        )
        lambda_ingestion_job.add_to_role_policy(lambda_ingestion_policy)
        # Add the S3 Put Event Source to the Lambda
        lambda_ingestion_job.add_event_source(S3EventSource(documentBucket,
            events=[s3.EventType.OBJECT_CREATED, s3.EventType.OBJECT_REMOVED],
        ))
        # Permission to Write Data to Tabel
        
        table.grant_write_data(self.kbQueryLambdaFunction)
        

        policy_statement = iam.PolicyStatement(
            actions=[
                "bedrock:Retrieve",
                "bedrock:RetrieveAndGenerate",
                "bedrock:InvokeModel"
            ],
            resources=[
                'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0',
                kbArn
            ]
        )

        self.kbQueryLambdaFunction.add_to_role_policy(policy_statement)
        
        api = apigateway.LambdaRestApi(
            self, 'KBQueryApiGW',
            handler=self.kbQueryLambdaFunction,
            proxy=False
        )

        kb_query = api.root.add_resource('query')
        kb_query.add_method('POST')
    
        CfnOutput(
            self, 'ApiEndpoint',
            value=api.url,
            description='The endpoint of the KB Query API'
        )
