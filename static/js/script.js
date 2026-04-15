function showOfficeForm() {
    const officeForm = document.getElementById("officeForm");
    const serviceForm = document.getElementById("serviceForm");

    if (officeForm) {
        officeForm.style.display = "block";
    }

    if (serviceForm) {
        serviceForm.style.display = "none";
    }
}

function showServiceForm() {
    const officeForm = document.getElementById("officeForm");
    const serviceForm = document.getElementById("serviceForm");

    if (serviceForm) {
        serviceForm.style.display = "block";
    }

    if (officeForm) {
        officeForm.style.display = "none";
    }
}