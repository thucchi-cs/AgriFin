// Function to count how many decimal places are in a number
function countDecimalPlaces(number) {
    let decimal = number.indexOf(".")
    if (decimal == -1) {
        return 0;
    }
    number = number.substring(decimal+1, number.length)
    return number.length;
}

document.querySelector(".btn-close").addEventListener("click", () => {
    let flash = document.querySelector("#flash-msg")
    flash.hidden = true
})

// Flash an alert
function flashMsg(msg) {
    let flash = document.querySelector("#flash-msg")
    flash.hidden = false;
    flash.querySelector("#msg").innerHTML = msg
    console.log("hi")
}

// Create bar graphs for income and expenses
function createBarGraph(element, labels, values, colors) {
    // Find average
    let avg = values.reduce((a, b) => a + b, 0)
    avg /= values.length
    avgData = Array(values.length).fill(avg)

    // Store data in array
    let data = {
        labels: labels,
        // Bars data
        datasets: [{
            data: values,
            backgroundColor: colors,
            order: 2,
            borderColor: "green",
            borderWidth: 2
        }, 
        // Average line data
        {
            data: avgData,
            type: "line",
            borderColor: "green",
            borderDash: [20,10],
            pointRadius: 0,
            pointHitRadius: 100,
            tension: 0,
            label: "avg",
            order: 1,
        }
        ]
    }

    // Create new chart
    return new Chart(
        // element to be drawn on
        element, {

        // plug in data
        type: "bar",
        data: data,

        // customizations
        options: {   
            responsive: true,
            plugins: {
                // No title or legend display
                legend: {
                    display: false,
                },
                title: {
                    display: false,
                },

                // Label units
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const value = context.parsed.y;
                            return `$${value.toFixed(2)}`
                        }
                    }
                }
            },

            // Axes scaling
            scales: {
                x: {
                    ticks: {
                        padding: 0
                    },
                    grid: {
                        offset: true
                    },
                    beginAtZero: true
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    })
    
}

// Create bar graphs of given time period and type
async function createAnalysisCharts(period, type) {
    // Get data from database
    const response = await fetch(`/get_chart_data?periods=${period}&type=${type}`)
    const result = await response.json()

    // Get element to be drawn on
    ctx = document.getElementById(type+"_chart_"+period)

    // Create array of colors - all green
    colors = Array(result.values.length).fill("rgba(8, 145, 8, 0.59)")

    // Create bar chart
    let chart = createBarGraph(ctx, result.labels, result.values, colors)
    return chart
}

// Initialize the charts in analysis tab
async function displayCharts() {
    // Create 4 bar graphs and 2 pie charts
    await createAnalysisCharts("weeks", "expenses")
    await createAnalysisCharts("months", "expenses")
    await createAnalysisCharts("weeks", "income")
    await createAnalysisCharts("months", "income")
    await createCategoriesChart("frequency")
    await createCategoriesChart("spending")
}

// Create Line graph of account balances over the month
function createLineGraph(element, labels, values, color) {
    // store data in Array
    let data = {
        labels: labels,
        datasets: [{
            data: values,
            borderColor: color,
            borderWidth: 5,
            pointHitRadius: 10
        }]
    }

    // Create line chart
    return new Chart(
        // Element to be drawn on
        element, {

        // Plug in data
        type: "line",
        data: data,

        // Customizations
        options: {   
            // Allow to hover anywhere

            interaction: {
                mode: 'nearest',     
                intersect: false     
              },
            responsive: true,
            plugins: {
                tooltip: {
                    mode: 'nearest',   
                    intersect: false,  

                    // Label units
                    callbacks: {
                        label: (context) => {
                            const value = context.parsed.y;
                            return `$${value.toFixed(2)}`
                        }
                    }
                },

                // Hide legend and title
                legend: {
                    display: false,
                },
                title: {
                    display: false,
                }
            },

            // Y axis scaling from 0
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    })
    
}

// Create balance chart on dashboard
async function createBalanceChart() {
    // Get data from database
    const response = await fetch("/balance")
    const result = await response.json()

    // Element to be drawn on
    ctx = document.getElementById("balance_chart")
    color = "green" // color

    // Create chart
    let chart = createLineGraph(ctx, result.labels, result.values, color)
    return chart
}

// Create pie charts
function createPieGraph(element, labels, values, type) {
    // Store data in array
    let data = {
        labels: labels,
        datasets: [{
            data: values
        }]
    }

    // Create new chart
    return new Chart(
        // Element to be drawn on
        element, {

        // Plug in data
        type: "pie",
        data: data,

        // Customizations
        options: {
            responsive: true,
            plugins: {
                // Hide title
                title: {
                    display: false,
                },
                tooltip: {
                    // Label units
                    callbacks: {
                        label: (context) => {
                            const value = context.parsed;
                            if (type == "frequency") {
                                return `${value} transactions`
                            }
                            return `$${value.toFixed(2)}`
                        }
                    }
                }
            }
        }
    })
    
}

// Create spending categories pie charts for analysis tab
async function createCategoriesChart(type) {
    // Get data from database
    const response = await fetch(`/categories?type=${type}`)
    const result = await response.json()

    // Element to be drawn on
    ctx = document.getElementById("categories_chart_"+type)
    color = "green" // color

    // Create chart
    let chart = createPieGraph(ctx, result.labels, result.values, type, "Spending Categories")
    return chart
}

// Switching tab logic
function switchTab(button, chart, period) {
    // Update button styles
    const parent = button.parentElement;
    Array.from(parent.children).forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');
    
    // Hide all canvases in the group
    const canvases = document.querySelectorAll(`canvas[id^="${chart}_"]`);
    canvases.forEach(canvas => canvas.classList.add('hidden'));
    
    // Show selected chart
    document.getElementById(`${chart}_chart_${period}`).classList.remove('hidden');
}
  
// Display charts on analysis tab
if (window.location.pathname == "/analysis") {
    displayCharts()
}

// Display balance chart on dashboard
if (window.location.pathname == "/dashboard") {
    chart = createBalanceChart()
}

// Add or edit transactions input validation
if ((window.location.pathname == "/add_transaction") || (window.location.pathname == "/edit_transaction")){
    // Get form to check validation
    let addTransaction = document.querySelector("#add_transaction")
    addTransaction.querySelector("#btn").addEventListener("click", function() {
        // Get inputs
        let amount = addTransaction.querySelector("#add_transac_amount").value;
        let type = addTransaction.querySelector("#add_transac_type").value;
        let date = addTransaction.querySelector("#add_transac_date").value;
        let category_income = addTransaction.querySelector("#add_transac_category_income").value;
        let category_expense = addTransaction.querySelector("#add_transac_category_expense").value;

        console.log(amount, type, date, "HIIII")

        // Flash error if not all fields are filled out
        if (!amount || (type == "Type") || !date || ((category_expense == "Select Category") && (category_income == "Select Category"))) {
            flashMsg("All required fields must be filled out!");
            return;
        }
    
        // Flash error for invalid amount number
        if (countDecimalPlaces(amount) > 2 || parseInt(amount) <= 0) {
            flashMsg("Invalid amount for transaction!")
            return
        }
    
        // Flash error for invalid date
        let today = new Date();
        date = new Date(date);
        console.log(today, date)
        if (date > today) {
            flashMsg("Invalid date!")
            return;
        }

        // Submit form if all inputs are valid
        addTransaction.submit()
    })

    // Show/Hide categoy field
    transac_type = document.querySelector("#add_transac_type")
    transac_type.addEventListener("change", () => {
        // Get type of transaction
        value = transac_type.value
        if (value == "expense") {
            // Show category field if type is expense
            document.querySelector("#add_transac_category_expense").hidden = false
            document.querySelector("#add_transac_category_income").hidden = true
        } else {
            // Hide category field if type is income
            document.querySelector("#add_transac_category_expense").hidden = true
            document.querySelector("#add_transac_category_income").hidden = false
        }
    })
}

// Transactions page
if (window.location.pathname == "/transactions") {
    // Initialize transaction to delete to none
    let transactionToDelete = null;

    // Pop up confirmation to delete
    function confirmDelete(transaction_id) {
        const popup = document.getElementById('delete-popup');
        popup.classList.remove('hidden');
        transactionToDelete = transaction_id;
    }

    // Close confirmation pop up
    function closePopup() {
        document.getElementById('delete-popup').classList.add('hidden');
        transactionToDelete = null;
    }

    // Delete if user click confirm to delete
    document.getElementById('confirm-delete').addEventListener('click', () => {
        if (transactionToDelete) {
            document.getElementById("delete-" + transactionToDelete).submit()
        }
        closePopup();
    });

    // Open/close sort panel
    sortPanel = document.getElementById("sortOptionsPanel")
    optionsBtn = document.getElementById("sortMenuToggle")
    optionsBtn.addEventListener("click", () => {
        sortPanel.classList.toggle("hidden")
    })

}

// Show / hide password
if (window.location.pathname == "/login" || window.location.pathname == "/register") {
    showPassword = document.getElementById("show-password")
    // When toggled
    showPassword.addEventListener("click", () => {
        passwords = document.querySelectorAll("#password_input")
        for (let password of passwords) {
            // change visibility
            if (showPassword.checked) {
                password.type = "text"
            } else {
                password.type = "password"
            }
        };
    })
}