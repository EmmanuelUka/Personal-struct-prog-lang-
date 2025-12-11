// Multi-function benchmark/test program

// Fibonacci function (recursive)
function fib(n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

// Factorial function (recursive)
function factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

// Sum of numbers from 1 to n (iterative)
function sum_to(n) {
    total = 0;
    i = 1;
    while (i <= n) {
        total = total + i;
        i = i + 1;
    }
    return total;
}

// Reverse an array
function reverse_array(arr) {
    result = [];
    i = len(arr) - 1;
    while (i >= 0) {
        result = result + [arr[i]];
        i = i - 1;
    }
    return result;
}

// Main program
print("Starting multi-function benchmark...");

// Test Fibonacci and Factorial
fib_sum = 0;
fact_sum = 0;
i = 0;
while (i < 10) {
    fib_sum = fib_sum + fib(i);
    fact_sum = fact_sum + factorial(i);
    i = i + 1;
}
print("Fib sum (0..9): " + str(fib_sum));
print("Factorial sum (0..9): " + str(fact_sum));

// Test sum_to
total_sum = sum_to(100);
print("Sum 1..100: " + str(total_sum));

// Test array operations
arr = [];
j = 0;
while (j < 50) {
    arr = arr + [j];
    j = j + 1;
}

print("Original array length: " + str(len(arr)));

rev = reverse_array(arr);
print("Reversed array length: " + str(len(rev)));

// Small CPU-heavy loop
cnt = 0;
k = 0;
while (k < 5000) {
    cnt = cnt + (k % 7);
    k = k + 1;
}

print("CPU loop result: " + str(cnt));

print("Benchmark complete.");
