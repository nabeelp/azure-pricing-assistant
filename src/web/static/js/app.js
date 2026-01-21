const state = {
    isDone: false,
    lastUserMessage: "",
    bomPollingInterval: null,
    pricingPollingInterval: null,
    lastBomUpdate: null,
    lastPricingUpdate: null,
    currentBomPollingRate: 3000,
    currentPricingPollingRate: 3000,
    errorTimeoutId: null,
    eventSource: null,
};

const dom = {
    chatContainer: null,
    proposalSection: null,
    proposalContent: null,
    bomSection: null,
    bomContent: null,
    bomStatusIndicator: null,
    bomStatusText: null,
    bomLastUpdated: null,
    pricingSummary: null,
    pricingTotal: null,
    pricingCurrency: null,
    pricingDate: null,
    pricingStatusText: null,
    doneBanner: null,
    errorBanner: null,
    errorBannerText: null,
    errorBannerClose: null,
    userInput: null,
    sendBtn: null,
    generateBtn: null,
    generateBtnSidebar: null,
    resetBtn: null,
    chatForm: null,
    backToChatBtn: null,
    newSessionBtn: null,
    progressIndicator: null,
    finalProposal: null,
    progressSteps: {},
};

function cacheDom() {
    dom.chatContainer = document.getElementById("chatContainer");
    dom.proposalSection = document.getElementById("proposalSection");
    dom.proposalContent = document.getElementById("proposalContent");
    dom.bomSection = document.getElementById("bomSection");
    dom.bomContent = document.getElementById("bomContent");
    dom.bomStatusIndicator = document.getElementById("bomStatusIndicator");
    dom.bomStatusText = document.getElementById("bomStatusText");
    dom.bomLastUpdated = document.getElementById("bomLastUpdated");
    dom.pricingSummary = document.getElementById("pricingSummary");
    dom.pricingTotal = document.getElementById("pricingTotal");
    dom.pricingCurrency = document.getElementById("pricingCurrency");
    dom.pricingDate = document.getElementById("pricingDate");
    dom.pricingStatusText = document.getElementById("pricingStatusText");
    dom.doneBanner = document.getElementById("doneBanner");
    dom.errorBanner = document.getElementById("errorBanner");
    dom.errorBannerText = document.getElementById("errorBannerText");
    dom.errorBannerClose = document.getElementById("errorBannerClose");
    dom.userInput = document.getElementById("userInput");
    dom.sendBtn = document.getElementById("sendBtn");
    dom.generateBtn = document.getElementById("generateBtn");  // Keep for backward compat
    dom.generateBtnSidebar = document.getElementById("generateBtnSidebar");
    dom.resetBtn = document.getElementById("resetBtn");
    dom.chatForm = document.getElementById("chatForm");
    dom.backToChatBtn = document.getElementById("backToChatBtn");
    dom.newSessionBtn = document.getElementById("newSessionBtn");
}

function setHidden(element, hidden) {
    if (!element) {
        return;
    }
    element.classList.toggle("hidden", hidden);
}

function startBOMPolling() {
    stopBOMPolling();
    state.bomPollingInterval = window.setInterval(
        pollBOMStatus,
        state.currentPollingRate,
    );
    pollBOMStatus();
}

function stopBOMPolling() {
    if (state.bomPollingInterval) {
        clearInterval(state.bomPollingInterval);
        state.bomPollingInterval = null;
    }
}

async function pollBOMStatus() {
    try {
        const response = await fetch("/api/bom");

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        // Update BOM if items are present
        if (data.bom_items && data.bom_items.length > 0) {
            updateBOM(data.bom_items, true);
        }
    } catch (error) {
        console.error("BOM polling error:", error);
    }
}

function updateBOMStatusIndicator(status, error) {
    if (!dom.bomStatusIndicator || !dom.bomStatusText) {
        return;
    }

    dom.bomStatusIndicator.className =
        "inline-flex h-2.5 w-2.5 rounded-full bg-slate-300";

    switch (status) {
        case "processing":
        case "queued":
            dom.bomStatusIndicator.classList.add(
                "bg-amber-500",
                "animate-pulse",
            );
            dom.bomStatusText.textContent = "Analyzing services...";
            break;
        case "error":
            dom.bomStatusIndicator.classList.add("bg-rose-500");
            dom.bomStatusText.textContent = error
                ? `Error: ${error}`
                : "Error processing BOM";
            break;
        case "complete":
            dom.bomStatusIndicator.classList.add("bg-emerald-500");
            dom.bomStatusText.textContent = "Services identified from conversation";
            break;
        case "idle":
        default:
            dom.bomStatusText.textContent = "Services identified from conversation";
            break;
    }
}

function updateBOMLastUpdated(lastUpdated) {
    if (!dom.bomLastUpdated) {
        return;
    }

    if (!lastUpdated) {
        dom.bomLastUpdated.textContent = "Last updated: —";
        return;
    }

    const parsed = new Date(lastUpdated);
    if (Number.isNaN(parsed.getTime())) {
        dom.bomLastUpdated.textContent = "Last updated: —";
        return;
    }

    dom.bomLastUpdated.textContent = `Last updated: ${parsed.toLocaleString()}`;
}

function adjustPollingRate(status) {
    let newRate;

    switch (status) {
        case "processing":
        case "queued":
            newRate = 1000;
            break;
        case "idle":
        case "complete":
        case "error":
            newRate = 5000;
            break;
        default:
            newRate = 3000;
    }

    if (Math.abs(newRate - state.currentBomPollingRate) >= 500) {
        state.currentBomPollingRate = newRate;
        if (state.bomPollingInterval) {
            clearInterval(state.bomPollingInterval);
            state.bomPollingInterval = window.setInterval(
                pollBOMStatus,
                state.currentBomPollingRate,
            );
        }
    }
}

function startPricingPolling() {
    stopPricingPolling();
    state.pricingPollingInterval = window.setInterval(
        pollPricingStatus,
        state.currentPricingPollingRate,
    );
    pollPricingStatus();
}

function stopPricingPolling() {
    if (state.pricingPollingInterval) {
        clearInterval(state.pricingPollingInterval);
        state.pricingPollingInterval = null;
    }
}

async function pollPricingStatus() {
    try {
        const response = await fetch("/api/pricing");

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        updatePricingSummary(
            data.pricing_total,
            data.pricing_currency,
            data.pricing_date,
            data.pricing_task_status,
            data.pricing_task_error
        );

        adjustPricingPollingRate(data.pricing_task_status);
    } catch (error) {
        console.error("Pricing polling error:", error);
    }
}

function updatePricingSummary(total, currency, date, status, error) {
    if (dom.pricingTotal) {
        dom.pricingTotal.textContent = `$${total.toFixed(2)}`;
    }

    if (dom.pricingCurrency) {
        dom.pricingCurrency.textContent = currency || "USD";
    }

    if (dom.pricingDate) {
        if (date) {
            dom.pricingDate.textContent = `as of ${date}`;
        } else {
            dom.pricingDate.textContent = "—";
        }
    }

    if (dom.pricingStatusText) {
        if (status === "processing" || status === "queued") {
            dom.pricingStatusText.classList.remove("hidden");
        } else {
            dom.pricingStatusText.classList.add("hidden");
        }

        if (status === "error" && error) {
            dom.pricingStatusText.classList.remove("hidden");
            dom.pricingStatusText.innerHTML = `<span class="text-rose-600">⚠️ ${error}</span>`;
        }
    }
}

function adjustPricingPollingRate(status) {
    let newRate;

    switch (status) {
        case "processing":
        case "queued":
            newRate = 1000;
            break;
        case "idle":
        case "complete":
        case "error":
            newRate = 5000;
            break;
        default:
            newRate = 3000;
    }

    if (Math.abs(newRate - state.currentPricingPollingRate) >= 500) {
        state.currentPricingPollingRate = newRate;
        if (state.pricingPollingInterval) {
            clearInterval(state.pricingPollingInterval);
            state.pricingPollingInterval = window.setInterval(
                pollPricingStatus,
                state.currentPricingPollingRate,
            );
        }
    }
}

function showErrorBanner(message) {
    if (!dom.errorBanner || !dom.errorBannerText) {
        return;
    }

    if (state.errorTimeoutId) {
        clearTimeout(state.errorTimeoutId);
        state.errorTimeoutId = null;
    }

    dom.errorBannerText.textContent = `❌ ${message}`;
    dom.errorBanner.classList.remove("hidden");

    state.errorTimeoutId = window.setTimeout(() => {
        hideErrorBanner();
    }, 10000);
}

function hideErrorBanner() {
    if (!dom.errorBanner) {
        return;
    }

    dom.errorBanner.classList.add("hidden");
}

function addErrorMessage(title, detail) {
    if (!dom.chatContainer) {
        return;
    }

    const errorDiv = document.createElement("div");
    errorDiv.className =
        "mb-4 flex gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-900 shadow-sm";

    const icon = document.createElement("span");
    icon.className = "text-2xl";
    icon.textContent = "⚠️";

    const content = document.createElement("div");
    content.className = "flex-1";

    const titleDiv = document.createElement("div");
    titleDiv.className = "text-sm font-semibold";
    titleDiv.textContent = title;

    const detailDiv = document.createElement("div");
    detailDiv.className = "mt-1 text-xs text-rose-700";
    detailDiv.textContent = detail;

    content.appendChild(titleDiv);
    content.appendChild(detailDiv);

    if (state.lastUserMessage) {
        const retryButton = document.createElement("button");
        retryButton.className =
            "mt-3 inline-flex items-center rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-100";
        retryButton.type = "button";
        retryButton.textContent = "🔄 Retry";
        retryButton.addEventListener("click", retryLastMessage);
        content.appendChild(retryButton);
    }

    errorDiv.appendChild(icon);
    errorDiv.appendChild(content);
    dom.chatContainer.appendChild(errorDiv);
    dom.chatContainer.scrollTop = dom.chatContainer.scrollHeight;
}

function retryLastMessage() {
    if (state.lastUserMessage && dom.userInput) {
        dom.userInput.value = state.lastUserMessage;
        sendMessage();
    }
}

async function sendMessage() {
    if (!dom.userInput || !dom.sendBtn) {
        return;
    }

    const message = dom.userInput.value.trim();

    if (!message) {
        return;
    }

    state.lastUserMessage = message;
    addMessage("user", message);
    dom.userInput.value = "";

    dom.sendBtn.disabled = true;
    dom.sendBtn.textContent = "Sending...";

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ message }),
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const errorMessage = data.error || `Server error (${response.status})`;
            showErrorBanner(errorMessage);
            addErrorMessage("Failed to process message", errorMessage);
            return;
        }

        if (data.error) {
            showErrorBanner(data.error);
            addErrorMessage("Chat Error", data.error);
            return;
        }

        if (data.response && data.response.trim()) {
            addMessage("assistant", data.response);
        }

        if (data.bom_items && data.bom_items.length > 0) {
            updateBOM(data.bom_items, data.pricing_items || [], data.bom_updated);
        }

        // Update pricing summary
        if (data.pricing_total !== undefined) {
            updatePricingSummary(
                data.pricing_total,
                data.pricing_currency,
                data.pricing_date,
                data.pricing_task_status,
                data.pricing_task_error
            );
        }

        if (data.is_done) {
            const summary =
                data.requirements_summary || "Requirements gathering complete";
            displayRequirementsSummary(summary);
        }
    } catch (error) {
        console.error("Chat error:", error);
        const errorDetail = error.message || "Unknown error occurred";
        showErrorBanner("Network error - please check your connection");
        addErrorMessage("Connection Error", `Failed to reach server: ${errorDetail}`);
    } finally {
        dom.sendBtn.disabled = false;
        dom.sendBtn.textContent = "Send";
    }
}

function appendTextWithLineBreaks(container, text) {
    const lines = text.split(/\r?\n/);
    lines.forEach((line, index) => {
        const span = document.createElement("span");
        span.textContent = line;
        container.appendChild(span);
        if (index < lines.length - 1) {
            container.appendChild(document.createElement("br"));
        }
    });
}

function displayRequirementsSummary(summary) {
    if (!dom.chatContainer || !dom.doneBanner || !dom.sendBtn || !dom.generateBtn) {
        return;
    }

    const summaryDiv = document.createElement("div");
    summaryDiv.className = "mb-4 flex justify-start";

    const summaryContent = document.createElement("div");
    summaryContent.className =
        "max-w-[70%] rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-relaxed text-slate-800 shadow-sm border-l-4 border-l-emerald-500";

    const title = document.createElement("strong");
    title.textContent = "📋 Requirements Summary:";

    const emphasis = document.createElement("em");
    emphasis.textContent = "Ready to proceed with proposal generation?";

    summaryContent.appendChild(title);
    summaryContent.appendChild(document.createElement("br"));
    summaryContent.appendChild(document.createElement("br"));
    appendTextWithLineBreaks(summaryContent, summary);
    summaryContent.appendChild(document.createElement("br"));
    summaryContent.appendChild(document.createElement("br"));
    summaryContent.appendChild(emphasis);

    summaryDiv.appendChild(summaryContent);
    dom.chatContainer.appendChild(summaryDiv);

    state.isDone = true;
    dom.doneBanner.classList.remove("hidden");
    setHidden(dom.sendBtn, true);
    
    // Show Generate Proposal button in sidebar instead of chat area
    if (dom.generateBtnSidebar) {
        dom.generateBtnSidebar.classList.remove("hidden");
    }

    dom.chatContainer.scrollTop = dom.chatContainer.scrollHeight;
}

function resetProgressTracking() {
    dom.progressSteps = {};
    dom.progressIndicator = null;
    dom.finalProposal = null;
}

function getProgressStepClasses(status) {
    const baseClasses =
        "flex items-center gap-3 rounded-xl border-2 bg-white p-3 transition";

    switch (status) {
        case "active":
            return `${baseClasses} border-indigo-500 bg-indigo-50`;
        case "complete":
            return `${baseClasses} border-emerald-400 bg-emerald-50`;
        case "error":
            return `${baseClasses} border-rose-400 bg-rose-50`;
        default:
            return `${baseClasses} border-slate-200`;
    }
}

function createProgressStep(id, iconText, titleText, agentName) {
    const step = document.createElement("div");
    step.className = getProgressStepClasses("idle");
    step.id = id;

    const icon = document.createElement("span");
    icon.className = "text-2xl";
    icon.textContent = iconText;

    const text = document.createElement("div");
    text.className = "flex-1";

    const title = document.createElement("div");
    title.className = "text-sm font-semibold text-slate-800";
    title.textContent = titleText;

    const status = document.createElement("div");
    status.className = "progress-status text-xs text-slate-500";
    status.textContent = "Waiting...";

    text.appendChild(title);
    text.appendChild(status);
    step.appendChild(icon);
    step.appendChild(text);

    dom.progressSteps[agentName] = step;
    return step;
}

function createProposalSkeleton() {
    if (!dom.proposalContent) {
        return;
    }

    resetProgressTracking();

    const progressIndicator = document.createElement("div");
    progressIndicator.className = "space-y-3 rounded-xl bg-slate-50 p-4";
    progressIndicator.id = "progressIndicator";

    progressIndicator.appendChild(
        createProgressStep("bomStep", "📋", "BOM Agent", "bom_agent"),
    );
    progressIndicator.appendChild(
        createProgressStep(
            "pricingStep",
            "💰",
            "Pricing Agent",
            "pricing_agent",
        ),
    );
    progressIndicator.appendChild(
        createProgressStep(
            "proposalStep",
            "📄",
            "Proposal Agent",
            "proposal_agent",
        ),
    );

    const finalProposal = document.createElement("div");
    finalProposal.id = "finalProposal";
    finalProposal.classList.add(
        "hidden",
        "whitespace-pre-wrap",
        "text-sm",
        "leading-relaxed",
        "text-slate-800",
    );

    dom.proposalContent.replaceChildren(progressIndicator, finalProposal);

    dom.progressIndicator = progressIndicator;
    dom.finalProposal = finalProposal;
}

function createErrorPanel(title, detail, actions) {
    const wrapper = document.createElement("div");
    wrapper.className =
        "flex gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-900 shadow-sm";

    const icon = document.createElement("span");
    icon.className = "text-2xl";
    icon.textContent = "⚠️";

    const content = document.createElement("div");
    content.className = "flex-1";

    const titleDiv = document.createElement("div");
    titleDiv.className = "text-sm font-semibold";
    titleDiv.textContent = title;

    const detailDiv = document.createElement("div");
    detailDiv.className = "mt-1 text-xs text-rose-700";
    detailDiv.textContent = detail;

    content.appendChild(titleDiv);
    content.appendChild(detailDiv);

    if (actions && actions.length > 0) {
        const actionsContainer = document.createElement("div");
        actionsContainer.className = "mt-3 flex flex-wrap gap-2";

        actions.forEach((action) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = action.secondary
                ? "inline-flex items-center rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-100"
                : "inline-flex items-center rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-700";
            button.textContent = action.label;
            button.addEventListener("click", action.onClick);
            actionsContainer.appendChild(button);
        });

        content.appendChild(actionsContainer);
    }

    wrapper.appendChild(icon);
    wrapper.appendChild(content);

    return wrapper;
}

async function generateProposal() {
    if (!dom.generateBtn || !dom.proposalSection || !dom.chatContainer || !dom.bomSection) {
        return;
    }

    dom.generateBtn.disabled = true;
    dom.generateBtn.textContent = "Generating...";

    dom.proposalSection.classList.remove("hidden");
    setHidden(dom.chatContainer, true);
    setHidden(dom.bomSection, true);
    createProposalSkeleton();

    try {
        if (state.eventSource) {
            state.eventSource.close();
            state.eventSource = null;
        }

        const eventSource = new EventSource("/api/generate-proposal-stream");
        state.eventSource = eventSource;

        eventSource.addEventListener("message", (event) => {
            const data = JSON.parse(event.data);

            if (data.error || data.event_type === "error") {
                eventSource.close();
                state.eventSource = null;

                const errorMsg = data.error || data.message || "Unknown error";
                showErrorBanner("Proposal generation failed");

                if (dom.proposalContent) {
                    const errorPanel = createErrorPanel(
                        "Failed to Generate Proposal",
                        errorMsg,
                        [
                            {
                                label: "🔄 Try Again",
                                onClick: () => {
                                    backToChat();
                                    generateProposal();
                                },
                            },
                            {
                                label: "← Back to Chat",
                                onClick: backToChat,
                                secondary: true,
                            },
                        ],
                    );
                    dom.proposalContent.replaceChildren(errorPanel);
                }

                dom.generateBtn.disabled = false;
                dom.generateBtn.textContent = "Generate Proposal";
                return;
            }

            const eventType = data.event_type;
            const agentName = data.agent_name;

            if (eventType === "agent_start") {
                updateProgressStep(agentName, "active", "Running...");
            } else if (eventType === "workflow_complete") {
                updateProgressStep("bom_agent", "complete", "Complete ✓");
                updateProgressStep("pricing_agent", "complete", "Complete ✓");
                updateProgressStep("proposal_agent", "complete", "Complete ✓");

                const proposalData = data.data || {};

                window.setTimeout(() => {
                    if (dom.progressIndicator) {
                        dom.progressIndicator.classList.add("hidden");
                    }
                    if (dom.finalProposal) {
                        dom.finalProposal.classList.remove("hidden");
                        dom.finalProposal.textContent =
                            proposalData.proposal || "No proposal generated";
                    }
                }, 500);

                eventSource.close();
                state.eventSource = null;
                dom.generateBtn.disabled = false;
                dom.generateBtn.textContent = "Generate Proposal";
            }
        });

        eventSource.addEventListener("error", () => {
            eventSource.close();
            state.eventSource = null;

            showErrorBanner("Lost connection to server");

            if (dom.proposalContent) {
                const errorPanel = createErrorPanel(
                    "Connection Lost",
                    "The connection to the server was interrupted. This may be due to network issues or server timeout.",
                    [
                        {
                            label: "🔄 Try Again",
                            onClick: () => {
                                backToChat();
                                generateProposal();
                            },
                        },
                        {
                            label: "← Back to Chat",
                            onClick: backToChat,
                            secondary: true,
                        },
                    ],
                );
                dom.proposalContent.replaceChildren(errorPanel);
            }

            dom.generateBtn.disabled = false;
            dom.generateBtn.textContent = "Generate Proposal";
        });
    } catch (error) {
        console.error("Proposal generation error:", error);
        showErrorBanner("Failed to start proposal generation");

        if (dom.proposalContent) {
            const errorPanel = createErrorPanel(
                "Unable to Generate Proposal",
                error.message || "An unexpected error occurred",
                [
                    {
                        label: "🔄 Try Again",
                        onClick: () => {
                            backToChat();
                            generateProposal();
                        },
                    },
                ],
            );
            dom.proposalContent.replaceChildren(errorPanel);
        }

        dom.generateBtn.disabled = false;
        dom.generateBtn.textContent = "Generate Proposal";
    }
}

function updateProgressStep(agentName, status, statusText) {
    const step = dom.progressSteps[agentName];
    if (!step) {
        return;
    }

    step.className = getProgressStepClasses(status);

    const statusDiv = step.querySelector(".progress-status");
    if (!statusDiv) {
        return;
    }

    statusDiv.replaceChildren();

    if (status === "active") {
        const spinner = document.createElement("span");
        spinner.className =
            "inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-500";
        statusDiv.appendChild(spinner);
        statusDiv.append(` ${statusText}`);
        return;
    }

    statusDiv.textContent = statusText;
}

function addMessage(role, content) {
    if (!dom.chatContainer) {
        return;
    }

    const messageDiv = document.createElement("div");
    const wrapperClasses = "mb-4 flex";
    messageDiv.className =
        role === "user"
            ? `${wrapperClasses} justify-end`
            : `${wrapperClasses} justify-start`;

    const contentDiv = document.createElement("div");
    const baseContentClasses =
        "max-w-[70%] whitespace-pre-wrap break-words rounded-xl px-4 py-3 text-sm leading-relaxed shadow-sm border";
    contentDiv.className =
        role === "user"
            ? `${baseContentClasses} bg-indigo-600 text-white border-indigo-600`
            : `${baseContentClasses} bg-white text-slate-800 border-slate-200`;
    contentDiv.textContent = content;

    messageDiv.appendChild(contentDiv);
    dom.chatContainer.appendChild(messageDiv);
    dom.chatContainer.scrollTop = dom.chatContainer.scrollHeight;
}

function updateBOM(bomItems, pricingItems, isNewUpdate) {
    if (!dom.bomContent) {
        return;
    }

    if (!bomItems || bomItems.length === 0) {
        dom.bomContent.innerHTML =
            '<div class="text-center text-slate-400 py-10">💬 Services and pricing will appear here as you discuss requirements</div>';
        return;
    }

    // Create a pricing lookup map by service+sku+region
    const pricingMap = new Map();
    if (pricingItems && pricingItems.length > 0) {
        pricingItems.forEach(item => {
            const key = `${item.serviceName}:${item.sku}:${item.armRegionName}`;
            pricingMap.set(key, item);
        });
    }

    dom.bomContent.replaceChildren();

    bomItems.forEach((bomItem) => {
        const itemDiv = document.createElement("div");
        itemDiv.className =
            "rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition";

        if (isNewUpdate) {
            itemDiv.classList.add("ring-2", "ring-emerald-400", "bg-emerald-50");
            window.setTimeout(() => {
                itemDiv.classList.remove(
                    "ring-2",
                    "ring-emerald-400",
                    "bg-emerald-50",
                );
            }, 1000);
        }

        const title = document.createElement("div");
        title.className = "text-sm font-semibold text-slate-800";
        title.textContent = bomItem.serviceName || "Unnamed service";

        const region = document.createElement("div");
        region.className = "text-xs text-slate-500";
        region.textContent = `📍 ${bomItem.region || "Unknown region"}`;

        const quantity = document.createElement("div");
        quantity.className = "text-xs text-slate-500";
        quantity.textContent = `🔢 Quantity: ${bomItem.quantity ?? "—"}`;

        const hours = document.createElement("div");
        hours.className = "text-xs text-slate-500";
        hours.textContent = `⏱️ ${bomItem.hours_per_month ?? "—"} hrs/month`;

        const sku = document.createElement("span");
        sku.className =
            "mt-2 inline-flex rounded bg-indigo-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white";
        sku.textContent = bomItem.sku || "Unknown SKU";

        itemDiv.appendChild(title);
        itemDiv.appendChild(region);
        itemDiv.appendChild(quantity);
        itemDiv.appendChild(hours);

        // Add pricing info if available
        const key = `${bomItem.serviceName}:${bomItem.sku}:${bomItem.armRegionName}`;
        const pricingItem = pricingMap.get(key);
        
        if (pricingItem) {
            const pricingDiv = document.createElement("div");
            pricingDiv.className = "mt-2 pt-2 border-t border-slate-200 space-y-1";

            const unitPrice = document.createElement("div");
            unitPrice.className = "text-xs text-slate-600";
            unitPrice.textContent = `💵 Unit: $${pricingItem.unit_price.toFixed(4)}/hr`;

            const monthlyCost = document.createElement("div");
            monthlyCost.className = "text-sm font-semibold text-indigo-600";
            const totalCost = pricingItem.monthly_cost * (bomItem.quantity || 1);
            monthlyCost.textContent = `💰 $${totalCost.toFixed(2)}/mo`;

            pricingDiv.appendChild(unitPrice);
            pricingDiv.appendChild(monthlyCost);

            if (pricingItem.notes) {
                const notes = document.createElement("div");
                notes.className = "text-xs text-amber-600 italic";
                notes.textContent = pricingItem.notes;
                pricingDiv.appendChild(notes);
            }

            itemDiv.appendChild(pricingDiv);
        } else {
            // Show pending pricing indicator
            const pendingDiv = document.createElement("div");
            pendingDiv.className = "mt-2 pt-2 border-t border-slate-200 text-xs text-slate-400 flex items-center gap-1";
            pendingDiv.innerHTML = `<span class="inline-block h-2.5 w-2.5 animate-spin rounded-full border-2 border-slate-200 border-t-slate-400"></span><span>Calculating price...</span>`;
            itemDiv.appendChild(pendingDiv);
        }

        itemDiv.appendChild(sku);
        dom.bomContent.appendChild(itemDiv);
    });
}

async function resetChat() {
    if (!confirm("Are you sure you want to start a new session? All progress will be lost.")) {
        return;
    }

    stopBOMPolling();
    stopPricingPolling();

    try {
        const response = await fetch("/api/reset", {
            method: "POST",
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMsg = errorData.error || "Failed to reset session";
            showErrorBanner(errorMsg);
            return;
        }

        if (dom.chatContainer) {
            dom.chatContainer.innerHTML = "";
        }

        if (dom.proposalContent) {
            dom.proposalContent.innerHTML = "";
        }

        if (dom.proposalSection) {
            dom.proposalSection.classList.add("hidden");
        }

        setHidden(dom.chatContainer, false);
        setHidden(dom.bomSection, false);

        if (dom.doneBanner) {
            dom.doneBanner.classList.add("hidden");
        }

        hideErrorBanner();
        setHidden(dom.sendBtn, false);
        
        // Hide sidebar Generate Proposal button
        if (dom.generateBtnSidebar) {
            dom.generateBtnSidebar.classList.add("hidden");
        }

        state.isDone = false;
        state.lastUserMessage = "";
        state.lastBomUpdate = null;
        state.lastPricingUpdate = null;

        updateBOM([], [], false);
        updatePricingSummary(0.0, "USD", null, "idle", null);

        startBOMPolling();
        startPricingPolling();
        addMessage("assistant", "Hello!\nI'm here to help you price an Azure solution. You can start by telling me the requirements, or give me a transcript from a customer meeting.");
    } catch (error) {
        console.error("Reset error:", error);
        showErrorBanner("Failed to reset session");
        addErrorMessage(
            "Reset Failed",
            `Unable to reset session: ${error.message || "Network error"}`,
        );
    }
}

function backToChat() {
    if (dom.proposalSection) {
        dom.proposalSection.classList.add("hidden");
    }
    setHidden(dom.chatContainer, false);
    setHidden(dom.bomSection, false);
    hideErrorBanner();
}

function handleFormSubmit(event) {
    event.preventDefault();
    sendMessage();
}

function attachEventHandlers() {
    if (dom.chatForm) {
        dom.chatForm.addEventListener("submit", handleFormSubmit);
    }

    // Support both old generateBtn (if exists) and new sidebar button
    if (dom.generateBtn) {
        dom.generateBtn.addEventListener("click", generateProposal);
    }
    
    if (dom.generateBtnSidebar) {
        dom.generateBtnSidebar.addEventListener("click", generateProposal);
    }

    if (dom.resetBtn) {
        dom.resetBtn.addEventListener("click", resetChat);
    }

    if (dom.backToChatBtn) {
        dom.backToChatBtn.addEventListener("click", backToChat);
    }

    if (dom.newSessionBtn) {
        dom.newSessionBtn.addEventListener("click", resetChat);
    }

    if (dom.errorBannerClose) {
        dom.errorBannerClose.addEventListener("click", hideErrorBanner);
    }
}

function initializeChat() {
    cacheDom();
    attachEventHandlers();
    addMessage("assistant", "Hello!\nI'm here to help you price an Azure solution. You can start by telling me the requirements, or give me a transcript from a customer meeting.");
    startBOMPolling();
    startPricingPolling();
}

window.addEventListener("DOMContentLoaded", initializeChat);

window.addEventListener("beforeunload", () => {
    stopBOMPolling();
    stopPricingPolling();
    if (state.eventSource) {
        state.eventSource.close();
        state.eventSource = null;
    }
});
