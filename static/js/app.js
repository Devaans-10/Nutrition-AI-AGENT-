// Frontend application logic for Nutrition AI Agent

document.addEventListener("DOMContentLoaded", function() {
    initTheme();
    setupProfileListeners();
    setupBmiListeners();
    setupChatListeners();
    setupMealPlannerListeners();
    setupDashboardListeners();
});

// --- THEME MANAGEMENT (DARK MODE) ---

function initTheme() {
    const savedTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateThemeIcon(savedTheme);

    const toggleBtn = document.getElementById("darkModeToggle");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", function() {
            const currentTheme = document.documentElement.getAttribute("data-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", newTheme);
            localStorage.setItem("theme", newTheme);
            updateThemeIcon(newTheme);
        });
    }
}

function updateThemeIcon(theme) {
    const themeIcon = document.getElementById("themeIcon");
    if (themeIcon) {
        if (theme === "dark") {
            themeIcon.className = "fa-solid fa-sun fs-5 text-warning";
        } else {
            themeIcon.className = "fa-solid fa-moon fs-5 text-secondary";
        }
    }
}

// --- PROFILE CRUD ---

function setupProfileListeners() {
    const form = document.getElementById("profileForm");
    if (!form) return;

    form.addEventListener("submit", function(e) {
        e.preventDefault();
        
        const profileId = document.getElementById("profileId").value;
        const payload = {
            name: document.getElementById("name").value,
            age: document.getElementById("age").value,
            gender: document.getElementById("gender").value,
            height_cm: document.getElementById("height").value,
            weight_kg: document.getElementById("weight").value,
            activity_level: document.getElementById("activity").value,
            diet_type: document.getElementById("diet").value,
            allergies: document.getElementById("allergies").value
        };

        const url = profileId ? `/api/profiles/update/${profileId}` : '/api/profiles';

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                window.location.reload();
            } else {
                alert("Error: " + data.message);
            }
        })
        .catch(err => console.error("Error saving profile:", err));
    });
}

function editProfile(profile) {
    document.getElementById("formTitle").innerText = "Edit Family Member";
    document.getElementById("submitBtn").innerText = "Update Profile";
    document.getElementById("cancelBtn").classList.remove("d-none");
    
    document.getElementById("profileId").value = profile.id;
    document.getElementById("name").value = profile.name;
    document.getElementById("age").value = profile.age;
    document.getElementById("gender").value = profile.gender;
    document.getElementById("height").value = profile.height_cm;
    document.getElementById("weight").value = profile.weight_kg;
    document.getElementById("activity").value = profile.activity_level;
    document.getElementById("diet").value = profile.diet_type;
    document.getElementById("allergies").value = profile.allergies || "";
    
    document.getElementById("name").focus();
}

function resetProfileForm() {
    document.getElementById("formTitle").innerText = "Add Family Member";
    document.getElementById("submitBtn").innerText = "Create Profile";
    document.getElementById("cancelBtn").classList.add("d-none");
    
    document.getElementById("profileId").value = "";
    document.getElementById("profileForm").reset();
}

function deleteProfile(profileId) {
    if (!confirm("Are you sure you want to delete this family profile? All chat history and logs will be lost.")) return;

    fetch(`/api/profiles/delete/${profileId}`, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            window.location.reload();
        } else {
            alert("Error: " + data.message);
        }
    })
    .catch(err => console.error("Error deleting profile:", err));
}

// --- BMI CALCULATOR ---

function setupBmiListeners() {
    const autofillSelect = document.getElementById("bmiAutofillSelect");
    const weightInput = document.getElementById("bmiWeight");
    const heightInput = document.getElementById("bmiHeight");
    const form = document.getElementById("bmiForm");

    if (autofillSelect) {
        autofillSelect.addEventListener("change", function() {
            const selectedOption = this.options[this.selectedIndex];
            const weight = selectedOption.getAttribute("data-weight");
            const height = selectedOption.getAttribute("data-height");
            
            if (weight && height) {
                weightInput.value = weight;
                heightInput.value = height;
            } else {
                weightInput.value = "";
                heightInput.value = "";
            }
        });
    }

    if (form) {
        form.addEventListener("submit", function(e) {
            e.preventDefault();
            
            const payload = {
                weight: weightInput.value,
                height: heightInput.value
            };

            fetch('/api/bmi/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const resultCard = document.getElementById("bmiResultCard");
                    resultCard.classList.remove("d-none");
                    
                    document.getElementById("bmiValue").innerText = data.bmi;
                    
                    const badge = document.getElementById("bmiCategoryBadge");
                    badge.innerText = data.category;
                    badge.className = `badge px-3 py-2 fs-6 mt-2 bg-${data.alert_class}`;
                    
                    document.getElementById("bmiTipText").innerText = data.tip;
                    
                    // Position pointer indicator on the visual bar (range 15 to 35)
                    let pct = ((data.bmi - 15) / (35 - 15)) * 100;
                    if (pct < 0) pct = 0;
                    if (pct > 100) pct = 100;
                    document.getElementById("bmiIndicator").style.left = `${pct}%`;
                    
                    resultCard.scrollIntoView({ behavior: 'smooth' });
                } else {
                    alert("Error: " + data.message);
                }
            })
            .catch(err => console.error("Error calculating BMI:", err));
        });
    }
}

// --- CHAT INTERFACE ---

function setupChatListeners() {
    const form = document.getElementById("chatForm");
    const input = document.getElementById("chatMessageInput");
    const chatBox = document.getElementById("chatBox");
    const profileIdInput = document.getElementById("chatProfileId");

    if (!form) return;

    // Handle Quick Prompts
    const quickPromptBtns = document.querySelectorAll(".quick-prompt-btn");
    quickPromptBtns.forEach(btn => {
        btn.addEventListener("click", function() {
            input.value = this.getAttribute("data-prompt");
            form.dispatchEvent(new Event("submit"));
        });
    });

    form.addEventListener("submit", function(e) {
        e.preventDefault();
        
        const message = input.value.trim();
        const profileId = profileIdInput.value;
        if (!message) return;

        // Clear input and remove empty state
        input.value = "";
        const emptyState = document.getElementById("chatEmptyState");
        if (emptyState) emptyState.remove();

        // Append User bubble
        appendChatBubble('user', message);
        
        // Show typing indicator
        const indicator = document.getElementById("chatTypingIndicator");
        indicator.classList.remove("d-none");
        chatBox.appendChild(indicator); // Move to bottom
        chatBox.scrollTop = chatBox.scrollHeight;

        // Call API
        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile_id: profileId, message: message })
        })
        .then(res => res.json())
        .then(data => {
            indicator.classList.add("d-none");
            if (data.success) {
                appendChatBubble('agent', data.response);
            } else {
                appendChatBubble('agent', "⚠️ Error: " + data.message);
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        })
        .catch(err => {
            indicator.classList.add("d-none");
            appendChatBubble('agent', "⚠️ Network connection failed.");
            chatBox.scrollTop = chatBox.scrollHeight;
            console.error(err);
        });
    });
}

function appendChatBubble(role, text) {
    const chatBox = document.getElementById("chatBox");
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role} ${role === 'user' ? 'align-self-end' : 'align-self-start'}`;
    
    // Simple markdown-to-HTML parser for bullet lists, bold texts, and tables
    let html = formatMarkdownToHtml(text);
    bubble.innerHTML = html;
    
    chatBox.appendChild(bubble);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function formatMarkdownToHtml(text) {
    // Escape standard HTML first
    let formatted = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Headings: ### heading
    formatted = formatted.replace(/^### (.*?)$/gm, '<h6 class="fw-bold mt-2">$1</h6>');
    formatted = formatted.replace(/^## (.*?)$/gm, '<h5 class="fw-bold mt-2">$1</h5>');
    formatted = formatted.replace(/^# (.*?)$/gm, '<h4 class="fw-bold mt-2">$1</h4>');

    // Bold text: **bold**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Bullet points: * item
    formatted = formatted.replace(/^\s*\*\s+(.*?)$/gm, '<li>$1</li>');
    // Group adjacent list items
    formatted = formatted.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');

    // Simple markdown tables
    // Matches standard markdown tables: | col1 | col2 |\n|---|---|\n| val1 | val2 |
    let tableRegex = /((?:\|[^\n]+\|\r?\n?)+)/g;
    formatted = formatted.replace(tableRegex, function(match) {
        let lines = match.trim().split('\n');
        if (lines.length < 2) return match;
        
        let htmlTable = '<div class="table-responsive"><table class="table table-bordered table-sm my-2">';
        
        lines.forEach((line, index) => {
            let cols = line.split('|').map(c => c.trim()).filter(c => c !== '');
            if (line.includes('---|') || line.includes('-:|') || line.includes(':-:|')) {
                // Divider row
                return;
            }
            htmlTable += '<tr>';
            cols.forEach(col => {
                if (index === 0) {
                    htmlTable += `<th class="bg-light small fw-bold">${col}</th>`;
                } else {
                    htmlTable += `<td class="small">${col}</td>`;
                }
            });
            htmlTable += '</tr>';
        });
        
        htmlTable += '</table></div>';
        return htmlTable;
    });

    // Newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');
    // Fix double <br> around lists/tables
    formatted = formatted.replace(/<\/ul><br>/g, '</ul>');
    formatted = formatted.replace(/<\/div><br>/g, '</div>');

    return formatted;
}

function clearActiveChat(profileId) {
    if (!confirm("Are you sure you want to clear this conversation history? This cannot be undone.")) return;
    
    fetch('/api/chat/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: profileId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            window.location.reload();
        } else {
            alert("Error: " + data.message);
        }
    })
    .catch(err => console.error(err));
}

// --- MEAL PLANNER INTERFACE ---

let activePlanData = null; // Stored state of selected plan

function setupMealPlannerListeners() {
    const form = document.getElementById("mealPlanForm");
    if (!form) return;

    form.addEventListener("submit", function(e) {
        e.preventDefault();
        
        const profileId = form.querySelector("[name='profile_id']").value;
        const goal = document.getElementById("goal").value;
        const duration = document.getElementById("duration").value;
        
        document.getElementById("mealPlanEmpty").classList.add("d-none");
        document.getElementById("mealPlanResult").classList.add("d-none");
        document.getElementById("mealPlanLoading").classList.remove("d-none");

        fetch('/api/meal-plan/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile_id: profileId, goal: goal, duration: duration })
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById("mealPlanLoading").classList.add("d-none");
            if (data.success) {
                renderMealPlan(data.plan);
            } else {
                alert("Generation failed: " + data.message);
                document.getElementById("mealPlanEmpty").classList.remove("d-none");
            }
        })
        .catch(err => {
            document.getElementById("mealPlanLoading").classList.add("d-none");
            document.getElementById("mealPlanEmpty").classList.remove("d-none");
            console.error(err);
        });
    });

    // Handle past plans click
    const pastPlanItems = document.querySelectorAll(".past-plan-item");
    pastPlanItems.forEach(item => {
        item.addEventListener("click", function() {
            try {
                const plan = JSON.parse(this.getAttribute("data-plan"));
                renderMealPlan(plan);
            } catch (e) {
                console.error("Error loading past plan", e);
            }
        });
    });
}

function renderMealPlan(plan) {
    activePlanData = plan;
    const resultDiv = document.getElementById("mealPlanResult");
    const emptyDiv = document.getElementById("mealPlanEmpty");
    const weeklyTabs = document.getElementById("weeklyTabs");
    
    emptyDiv.classList.add("d-none");
    resultDiv.classList.remove("d-none");

    document.getElementById("planTitle").innerText = plan.title;
    document.getElementById("planCalTarget").innerText = `${plan.target_calories} kcal`;
    document.getElementById("planProtein").innerText = `${plan.target_protein}g`;
    document.getElementById("planCarbs").innerText = `${plan.target_carbs}g`;
    document.getElementById("planFat").innerText = `${plan.target_fat}g`;

    if (plan.days.length > 1) {
        // Weekly plan
        weeklyTabs.classList.remove("d-none");
        weeklyTabs.innerHTML = "";
        
        plan.days.forEach((dayObj, index) => {
            const li = document.createElement("li");
            li.className = "nav-item";
            li.innerHTML = `
                <button class="nav-link ${index === 0 ? 'active' : ''} btn-sm me-1" 
                        onclick="showMealDay(${index})" 
                        id="day-tab-${index}" 
                        type="button">
                    Day ${index + 1}
                </button>
            `;
            weeklyTabs.appendChild(li);
        });
        showMealDay(0);
    } else {
        // Daily plan
        weeklyTabs.classList.add("d-none");
        populateMealsGrid(plan.days[0].meals);
    }
}

function showMealDay(dayIndex) {
    if (!activePlanData) return;
    
    // Update active tab class
    const tabs = document.querySelectorAll("#weeklyTabs button");
    tabs.forEach((tab, index) => {
        if (index === dayIndex) {
            tab.classList.add("active");
        } else {
            tab.classList.remove("active");
        }
    });

    populateMealsGrid(activePlanData.days[dayIndex].meals);
}

function populateMealsGrid(meals) {
    // breakfast
    document.getElementById("bfName").innerText = meals.breakfast.name;
    document.getElementById("bfCalories").innerText = `${meals.breakfast.calories} kcal`;
    document.getElementById("bfDescription").innerText = meals.breakfast.description;
    document.getElementById("bfP").innerText = `${meals.breakfast.protein}g`;
    document.getElementById("bfC").innerText = `${meals.breakfast.carbs}g`;
    document.getElementById("bfF").innerText = `${meals.breakfast.fat}g`;

    // lunch
    document.getElementById("lhName").innerText = meals.lunch.name;
    document.getElementById("lhCalories").innerText = `${meals.lunch.calories} kcal`;
    document.getElementById("lhDescription").innerText = meals.lunch.description;
    document.getElementById("lhP").innerText = `${meals.lunch.protein}g`;
    document.getElementById("lhC").innerText = `${meals.lunch.carbs}g`;
    document.getElementById("lhF").innerText = `${meals.lunch.fat}g`;

    // snack
    document.getElementById("skName").innerText = meals.snack.name;
    document.getElementById("skCalories").innerText = `${meals.snack.calories} kcal`;
    document.getElementById("skDescription").innerText = meals.snack.description;
    document.getElementById("skP").innerText = `${meals.snack.protein}g`;
    document.getElementById("skC").innerText = `${meals.snack.carbs}g`;
    document.getElementById("skF").innerText = `${meals.snack.fat}g`;

    // dinner
    document.getElementById("dnName").innerText = meals.dinner.name;
    document.getElementById("dnCalories").innerText = `${meals.dinner.calories} kcal`;
    document.getElementById("dnDescription").innerText = meals.dinner.description;
    document.getElementById("dnP").innerText = `${meals.dinner.protein}g`;
    document.getElementById("dnC").innerText = `${meals.dinner.carbs}g`;
    document.getElementById("dnF").innerText = `${meals.dinner.fat}g`;
}

// --- DASHBOARD AND CHART ACTIONS ---

let calorieChartInstance = null;

function setupDashboardListeners() {
    const quickLogForm = document.getElementById("quickFoodLogForm");
    if (!quickLogForm) return;

    quickLogForm.addEventListener("submit", function(e) {
        e.preventDefault();
        
        const profileId = document.getElementById("logProfileId").value;
        const foodDesc = document.getElementById("foodDescription").value.trim();
        const logBtn = document.getElementById("logFoodBtn");
        const spinner = document.getElementById("logSpinner");
        const resultPanel = document.getElementById("logResultPanel");
        const analysisText = document.getElementById("logAnalysisText");

        if (!foodDesc) return;

        // Show spinner
        logBtn.setAttribute("disabled", "true");
        spinner.classList.remove("d-none");
        resultPanel.classList.add("d-none");

        fetch('/api/nutrition/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile_id: profileId, food_description: foodDesc })
        })
        .then(res => res.json())
        .then(data => {
            logBtn.removeAttribute("disabled");
            spinner.classList.add("d-none");

            if (data.success) {
                // Reset form
                quickLogForm.reset();

                // Show parse response
                resultPanel.classList.remove("d-none");
                const analysis = data.analysis;
                analysisText.innerHTML = `
                    <strong>Logged:</strong> Calories: ${analysis.calories} kcal | 
                    Protein: ${analysis.protein}g | Carbs: ${analysis.carbs}g | Fat: ${analysis.fat}g<br>
                    <span class="text-secondary font-italic">Tip: ${analysis.suggestions}</span>
                `;

                // Update Progress metrics
                updateProgressMeters(data.daily_total);
                
                // Redraw charts
                initDashboardCharts(profileId);
            } else {
                alert("Logging failed: " + data.message);
            }
        })
        .catch(err => {
            logBtn.removeAttribute("disabled");
            spinner.classList.add("d-none");
            console.error(err);
        });
    });
}

function updateProgressMeters(dailyTotal) {
    // Retrieve targets from dashboard DOM or recalculate
    const targetCal = parseInt(document.getElementById("dashCalVal").parentNode.textContent.split("/")[1]);
    
    // Update numerical texts
    document.getElementById("dashCalVal").innerText = dailyTotal.calories;
    document.getElementById("dashProVal").innerText = dailyTotal.protein;
    document.getElementById("dashCarbVal").innerText = dailyTotal.carbs;
    document.getElementById("dashFatVal").innerText = dailyTotal.fat;
    
    // Update widths of progress bars
    let calPct = (dailyTotal.calories / targetCal) * 100;
    if (calPct > 100) calPct = 100;
    document.getElementById("dashCalBar").style.width = `${calPct}%`;
}

function initDashboardCharts(profileId) {
    const ctx = document.getElementById("caloriesChart");
    if (!ctx) return;

    fetch(`/api/nutrition-stats/${profileId}`)
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const labels = data.labels.length > 0 ? data.labels : ["No Data"];
            const caloriesData = data.calories.length > 0 ? data.calories : [0];
            const targetLine = Array(labels.length).fill(data.targets.calories);

            // Destroy previous instance to re-draw
            if (calorieChartInstance) {
                calorieChartInstance.destroy();
            }

            calorieChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Calories Ingested (kcal)',
                            data: caloriesData,
                            backgroundColor: 'rgba(46, 125, 50, 0.15)',
                            borderColor: '#2e7d32',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.3,
                            pointBackgroundColor: '#2e7d32',
                            pointRadius: 5
                        },
                        {
                            label: 'Daily Target Line',
                            data: targetLine,
                            borderColor: '#e53e3e',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            fill: false,
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: getComputedStyle(document.documentElement).getPropertyValue('--border-color') || 'rgba(0,0,0,0.05)'
                            },
                            ticks: {
                                color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted') || '#64748b'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted') || '#64748b'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: getComputedStyle(document.documentElement).getPropertyValue('--text-color') || '#1e293b'
                            }
                        }
                    }
                }
            });
        }
    })
    .catch(err => console.error("Error updating charts:", err));
}
