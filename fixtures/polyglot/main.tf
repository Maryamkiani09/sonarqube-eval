# Terraform fixture (IaC analysis)
resource "aws_s3_bucket" "logs" {
  bucket = "shopflow-logs"
  acl    = "public-read"
}

resource "aws_security_group_rule" "ssh" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = "sg-0123456789"
}
