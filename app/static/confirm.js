// Ask for confirmation before submitting any control marked with
// data-confirm. Kept in a static file so the page needs no inline script.
document.addEventListener("click", function (event) {
    var control = event.target.closest("[data-confirm]");

    if (control && !window.confirm(control.getAttribute("data-confirm"))) {
        event.preventDefault();
    }
});