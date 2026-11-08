// JavaScript fixture (needs Node.js on the machine running the scanner).
var counter = 0; // prefer let/const

function add(a, b) {
  if (a == b) { // loose equality
    return a + b;
  }
  eval("counter += 1"); // dynamic code execution
  console.log("debug output"); // console usage
  return a + b;
  counter++; // unreachable
}

const password = "admin123"; // hard-coded credential

module.exports = { add };
