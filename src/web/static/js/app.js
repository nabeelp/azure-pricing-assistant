const state = {
    isDone: false,
    lastUserMessage: "",
    bomPollingInterval: null,
    lastBomUpdate: null,
    currentPollingRate: 3000,
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
    doneBanner: null,
    errorBanner: null,
    errorBannerText: null,
    errorBannerClose: null,
    userInput: null,
    sendBtn: null,
    generateBtn: null,
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
    dom.doneBanner = document.getElementById("doneBanner");
    dom.errorBanner = document.getElementById("errorBanner");
    dom.errorBannerText = document.getElementById("errorBannerText");
    dom.errorBannerClose = document.getElementById("errorBannerClose");
    dom.userInput = document.getElementById("userInput");
    dom.sendBtn = document.getElementById("sendBtn");
    dom.generateBtn = document.getElementById("generateBtn");
    dom.resetBtn = document.getElementById("resetBtn");
    dom.chatForm = document.getElementById("chatForm");
    dom.backToChatBtn = document.getElementById("backToChatBtn");
    dom.newSessionBtn = document.getElementById("newSessionBtn");
}

function setHidden(element, hidden) {
    if (!element) {
        return;
    }
    element.classList.toggle("is-hidden", hidden);
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

        updateBOMStatusIndicator(data.bom_task_status, data.bom_task_error);
        updateBOMLastUpdated(data.bom_last_update);

        const bomUpdated = data.bom_last_update !== state.lastBomUpdate;
        if (bomUpdated) {
            state.lastBomUpdate = data.bom_last_update;

            if (data.bom_items && data.bom_items.length > 0) {
                updateBOM(data.bom_items, true);
            }
        }

        adjustPollingRate(data.bom_task_status);
    } catch (error) {
        console.error("BOM polling error:", error);
    }
}

function updateBOMStatusIndicator(status, error) {
    if (!dom.bomStatusIndicator || !dom.bomStatusText) {
        return;
    }

    dom.bomStatusIndicator.className = "bom-status-indicator";

    switch (status) {
        case "processing":
        case "queued":
            dom.bomStatusIndicator.classList.add("processing");
            dom.bomStatusText.textContent = "Analyzing services...";
            break;
        case "error":
            dom.bomStatusIndicator.classList.add("error");
            dom.bomStatusText.textContent = error
                ? `Error: ${error}`
                : "Error processing BOM";
            break;
        case "complete":
            dom.bomStatusIndicator.classList.add("complete");
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

    if (Math.abs(newRate - state.currentPollingRate) >= 500) {
        state.currentPollingRate = newRate;
        if (state.bomPollingInterval) {
            clearInterval(state.bomPollingInterval);
            state.bomPollingInterval = window.setInterval(
                pollBOMStatus,
                state.currentPollingRate,
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
    dom.errorBanner.classList.add("active");

    state.errorTimeoutId = window.setTimeout(() => {
        hideErrorBanner();
    }, 10000);
}

function hideErrorBanner() {
    if (!dom.errorBanner) {
        return;
    }

    dom.errorBanner.classList.remove("active");
}

function addErrorMessage(title, detail) {
    if (!dom.chatContainer) {
        return;
    }

    const errorDiv = document.createElement("div");
    errorDiv.className = "error-message";

    const icon = document.createElement("span");
    icon.className = "error-message-icon";
    icon.textContent = "⚠️";

    const content = document.createElement("div");
    content.className = "error-message-content";

    const titleDiv = document.createElement("div");
    titleDiv.className = "error-message-title";
    titleDiv.textContent = title;

    const detailDiv = document.createElement("div");
    detailDiv.className = "error-message-detail";
    detailDiv.textContent = detail;

    content.appendChild(titleDiv);
    content.appendChild(detailDiv);

    if (state.lastUserMessage) {
        const retryButton = document.createElement("button");
        retryButton.className = "retry-button";
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

        if (data.bom_task_status) {
            updateBOMStatusIndicator(data.bom_task_status, data.bom_task_error);
        }

        if (data.bom_items && data.bom_items.length > 0) {
            updateBOM(data.bom_items, data.bom_updated);
        }

        if (data.bom_last_update) {
            updateBOMLastUpdated(data.bom_last_update);
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
    summaryDiv.className = "message assistant";

    const summaryContent = document.createElement("div");
    summaryContent.className = "message-content summary";

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
    dom.doneBanner.classList.add("active");
    setHidden(dom.sendBtn, true);
    setHidden(dom.generateBtn, false);

    dom.chatContainer.scrollTop = dom.chatContainer.scrollHeight;
}

function resetProgressTracking() {
    dom.progressSteps = {};
    dom.progressIndicator = null;
    dom.finalProposal = null;
}

function createProgressStep(id, iconText, titleText, agentName) {
    const step = document.createElement("div");
    step.className = "progress-step";
    step.id = id;

    const icon = document.createElement("span");
    icon.className = "progress-icon";
    icon.textContent = iconText;

    const text = document.createElement("div");
    text.className = "progress-text";

    const title = document.createElement("div");
    title.className = "progress-title";
    title.textContent = titleText;

    const status = document.createElement("div");
    status.className = "progress-status";
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
    progressIndicator.className = "progress-indicator";
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
    finalProposal.classList.add("is-hidden");

    dom.proposalContent.replaceChildren(progressIndicator, finalProposal);

    dom.progressIndicator = progressIndicator;
    dom.finalProposal = finalProposal;
}

function createErrorPanel(title, detail, actions) {
    const wrapper = document.createElement("div");
    wrapper.className = "error-message";

    const icon = document.createElement("span");
    icon.className = "error-message-icon";
    icon.textContent = "⚠️";

    const content = document.createElement("div");
    content.className = "error-message-content";

    const titleDiv = document.createElement("div");
    titleDiv.className = "error-message-title";
    titleDiv.textContent = title;

    const detailDiv = document.createElement("div");
    detailDiv.className = "error-message-detail";
    detailDiv.textContent = detail;

    content.appendChild(titleDiv);
    content.appendChild(detailDiv);

    if (actions && actions.length > 0) {
        const actionsContainer = document.createElement("div");
        actionsContainer.className = "button-group";

        actions.forEach((action) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = action.secondary
                ? "retry-button secondary"
                : "retry-button";
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

    dom.proposalSection.classList.add("active");
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
                        dom.progressIndicator.classList.add("is-hidden");
                    }
                    if (dom.finalProposal) {
                        dom.finalProposal.classList.remove("is-hidden");
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

    step.className = `progress-step ${status}`;

    const statusDiv = step.querySelector(".progress-status");
    if (!statusDiv) {
        return;
    }

    statusDiv.replaceChildren();

    if (status === "active") {
        const spinner = document.createElement("span");
        spinner.className = "spinner";
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
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.textContent = content;

    messageDiv.appendChild(contentDiv);
    dom.chatContainer.appendChild(messageDiv);
    dom.chatContainer.scrollTop = dom.chatContainer.scrollHeight;
}

function updateBOM(bomItems, isNewUpdate) {
    if (!dom.bomContent) {
        return;
    }

    if (!bomItems || bomItems.length === 0) {
        dom.bomContent.innerHTML =
            '<div class="bom-empty">💬 BOM will appear here as you discuss requirements</div>';
        return;
    }

    dom.bomContent.replaceChildren();

    bomItems.forEach((item) => {
        const itemDiv = document.createElement("div");
        itemDiv.className = "bom-item";

        if (isNewUpdate) {
            itemDiv.classList.add("new");
            window.setTimeout(() => itemDiv.classList.remove("new"), 1000);
        }

        const title = document.createElement("div");
        title.className = "bom-item-title";
        title.textContent = item.serviceName || "Unnamed service";

        const region = document.createElement("div");
        region.className = "bom-item-detail";
        region.textContent = `📍 ${item.region || "Unknown region"}`;

        const quantity = document.createElement("div");
        quantity.className = "bom-item-detail";
        quantity.textContent = `🔢 Quantity: ${item.quantity ?? "—"}`;

        const hours = document.createElement("div");
        hours.className = "bom-item-detail";
        hours.textContent = `⏱️ ${item.hours_per_month ?? "—"} hrs/month`;

        const sku = document.createElement("span");
        sku.className = "bom-item-sku";
        sku.textContent = item.sku || "Unknown SKU";

        itemDiv.appendChild(title);
        itemDiv.appendChild(region);
        itemDiv.appendChild(quantity);
        itemDiv.appendChild(hours);
        itemDiv.appendChild(sku);
        dom.bomContent.appendChild(itemDiv);
    });
}

async function resetChat() {
    if (!confirm("Are you sure you want to start a new session? All progress will be lost.")) {
        return;
    }

    stopBOMPolling();

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
            dom.proposalSection.classList.remove("active");
        }

        setHidden(dom.chatContainer, false);
        setHidden(dom.bomSection, false);

        if (dom.doneBanner) {
            dom.doneBanner.classList.remove("active");
        }

        hideErrorBanner();
        setHidden(dom.sendBtn, false);
        setHidden(dom.generateBtn, true);

        state.isDone = false;
        state.lastUserMessage = "";
        state.lastBomUpdate = null;

        updateBOM([], false);
        updateBOMLastUpdated(null);
        updateBOMStatusIndicator("idle", null);

        startBOMPolling();
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
        dom.proposalSection.classList.remove("active");
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

    if (dom.generateBtn) {
        dom.generateBtn.addEventListener("click", generateProposal);
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
}

window.addEventListener("DOMContentLoaded", initializeChat);

window.addEventListener("beforeunload", () => {
    stopBOMPolling();
    if (state.eventSource) {
        state.eventSource.close();
        state.eventSource = null;
    }
});
