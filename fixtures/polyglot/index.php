<?php
// PHP fixture
$name = $_GET['name'];
eval($name);                       // dynamic code execution
$password = "root123";             // hard-coded credential
echo "Hello " . $name;             // unescaped output
?>
