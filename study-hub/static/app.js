const timerElement = document.querySelector("#timer");
const startButton = document.querySelector("#timer-start");
const resetButton = document.querySelector("#timer-reset");

if (timerElement && startButton && resetButton) {
    let remainingSeconds = 25 * 60;
    let intervalId = null;

    document.querySelectorAll(".timer-presets button").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".timer-presets button").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            window.clearInterval(intervalId);
            intervalId = null;
            remainingSeconds = Number(button.dataset.minutes) * 60;
            startButton.textContent = "Start";
            renderTimer();
        });
    });

    function renderTimer() {
        const minutes = Math.floor(remainingSeconds / 60);
        const seconds = remainingSeconds % 60;
        timerElement.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }

    startButton.addEventListener("click", () => {
        if (intervalId) {
            window.clearInterval(intervalId);
            intervalId = null;
            startButton.textContent = "Resume";
            return;
        }

        startButton.textContent = "Pause";
        intervalId = window.setInterval(() => {
            remainingSeconds -= 1;
            if (remainingSeconds <= 0) {
                window.clearInterval(intervalId);
                intervalId = null;
                remainingSeconds = 0;
                startButton.textContent = "Finished";
            }
            renderTimer();
        }, 1000);
    });

    resetButton.addEventListener("click", () => {
        window.clearInterval(intervalId);
        intervalId = null;
        remainingSeconds = 25 * 60;
        startButton.textContent = "Start";
        renderTimer();
    });
}

const goalFormButton = document.querySelector("#show-goal-form");
const goalForm = document.querySelector("#goal-form");
if (goalFormButton && goalForm) {
    goalFormButton.addEventListener("click", () => {
        goalForm.classList.toggle("is-open");
    });
}

const printLessonsButton = document.querySelector("#print-lessons");
if (printLessonsButton) {
    printLessonsButton.addEventListener("click", () => {
        window.print();
    });
}

document.querySelectorAll(".lesson-quiz").forEach((quiz) => {
    const feedback = quiz.querySelector(".quiz-feedback");
    const answer = quiz.querySelector("details > p");
    const choices = quiz.querySelectorAll(".quiz-choice");

    choices.forEach((choice) => {
        choice.addEventListener("click", () => {
            choices.forEach((item) => {
                item.setAttribute("aria-pressed", String(item === choice));
                item.classList.toggle("is-selected", item === choice);
            });

            const response = choice.dataset.correct === "true"
                ? "Yes! "
                : "Good thinking! Let's explore: ";
            feedback.textContent = response + answer.textContent;
        });
    });
});
