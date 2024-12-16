#!/usr/bin/env python3
import os

import aws_cdk as cdk

from healthapp.healthapp_stack import HealthappStack


app = cdk.App()
HealthappStack(app, "HealthappStack",

    )

app.synth()
