data "aws_cloudfront_distribution" "f1_api" {
  count = var.cloudfront_distribution_id == "" ? 0 : 1
  id = var.cloudfront_distribution_id
}
