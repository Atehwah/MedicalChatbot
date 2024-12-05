#!/usr/bin/env python3
import os

import aws_cdk as cdk

from healthapp.healthapp_stack import HealthappStack


app = cdk.App()
HealthappStack(app, "HealthappStack",
    # env=cdk.Environment(account='059609450404', region='us-east-1'),
    )

app.synth()
