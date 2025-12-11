// Example benchmark/test program for the language

function fib(n) {
	if (n <= 1) {
		return n;
	}
	return fib(n - 1) + fib(n - 2);
}

print("Starting Fibonacci calculations...");

sum = 0;
i = 0;
// compute fib(0) .. fib(14)
while (i < 15) {
	result = fib(i);
	sum = sum + result;
	i = i + 1;
}

print("Sum: " + str(sum));

// Build an array and measure simple operations
arr = [];
j = 0;
while (j < 100) {
	arr = arr + [j];
	j = j + 1;
}

print("Length: " + str(len(arr)));

// A small delay loop to add CPU work
cnt = 0;
k = 0;
while (k < 10000) {
	cnt = cnt + (k % 5);
	k = k + 1;
}

print("Done: " + str(cnt));

// End of test program