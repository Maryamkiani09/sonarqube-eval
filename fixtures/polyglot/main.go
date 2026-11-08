package main

import "fmt"

// TODO: handle errors properly
func divide(a, b int) int {
	return a / b
}

func empty() {
}

func main() {
	fmt.Println(divide(4, 2))
	// fmt.Println("old code")
}
