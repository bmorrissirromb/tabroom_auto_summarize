locals {
  account_id            = data.aws_caller_identity.current.account_id
  protected_branch_name = "main"
  # rvm_assumption_policy = jsonencode({
  #   "Version" : "2012-10-17",
  #   "Statement" : [
  #     {
  #       "Effect" : "Allow",
  #       "Action" : [
  #         "sts:TagSession",
  #         "sts:SetSourceIdentity",
  #         "sts:AssumeRole"
  #       ],
  #       "Resource" : [
  #         "arn:aws:iam::*:role/${var.iam_assuming_role_name}"
  #       ]
  #     }
  #   ]
  # })
  # rvm_readonly_assumption_policy = jsonencode({
  #   "Version" : "2012-10-17",
  #   "Statement" : [
  #     {
  #       "Effect" : "Allow",
  #       "Action" : [
  #         "sts:TagSession",
  #         "sts:SetSourceIdentity",
  #         "sts:AssumeRole"
  #       ],
  #       "Resource" : [
  #         "arn:aws:iam::*:role/${var.iam_assuming_role_name}-readonly"
  #       ]
  #     }
  #   ]
  # })
  tabroom_modify_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "s3:*",
        ],
        "Resource" : [
          "arn:aws:s3:::tabroomsummary.com",
          "arn:aws:s3:::tabroomsummary.com/*",
          "arn:aws:s3:::docker-selenium-lambda-ta-serverlessdeploymentbuck-dsqpcfvopg4c/serverless/docker-selenium-lambda-tabroom/*"
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "lambda:*",
        ],
        "Resource" : [
          "arn:aws:lambda:us-east-1:238589881750:function:api_lambda_function"
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ecr:*",
        ],
        "Resource" : [
          "arn:aws:ecr:us-east-1:238589881750:repository/serverless-docker-selenium-lambda-tabroom-prod"
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "cloudformation:*",
        ],
        "Resource" : [
          "arn:aws:cloudformation:us-east-1:238589881750:stack/docker-selenium-lambda-tabroom-prod",
          "arn:aws:cloudformation:us-east-1:238589881750:stack/docker-selenium-lambda-tabroom-prod/*"
        ]
      }
    ]
  })
  terraform_state_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
        ],
        "Resource" : [
          "arn:aws:s3:::${local.account_id}-${var.bucket_suffix}",
          "arn:aws:s3:::${local.account_id}-${var.bucket_suffix}/*",
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ],
        "Resource" : [
          "arn:aws:dynamodb:*:${local.account_id}:table/${var.ddb_lock_table_name}"
        ]
      }
    ]
  })
}
