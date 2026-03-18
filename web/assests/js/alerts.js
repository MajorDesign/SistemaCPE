/**
 * ============================================================
 * SISTEMA DE ALERTAS (Erros e Sucessos)
 * ============================================================
 */

/**
 * Mostra mensagem de erro
 */
function showError(message, alertBoxId = "alertBox", alertMessageId = "alertMessage") {
    const alertBox = document.getElementById(alertBoxId);
    const alertMessage = document.getElementById(alertMessageId);
    
    if (alertBox && alertMessage) {
      alertMessage.textContent = message;
      alertBox.classList.remove("d-none");
      setTimeout(() => {
        alertBox.classList.add("d-none");
      }, 5000);
    }
  }
  
  /**
   * Mostra mensagem de sucesso
   */
  function showSuccess(message, successBoxId = "successBox", successMessageId = "successMessage") {
    const successBox = document.getElementById(successBoxId);
    const successMessage = document.getElementById(successMessageId);
    
    if (successBox && successMessage) {
      successMessage.textContent = message;
      successBox.classList.remove("d-none");
      setTimeout(() => {
        successBox.classList.add("d-none");
      }, 5000);
    }
  }
  
  /**
   * Mostra mensagem de erro no modal
   */
  function showModalError(message, modalAlertBoxId = "modalAlertBox", modalAlertMessageId = "modalAlertMessage") {
    const modalAlert = document.getElementById(modalAlertBoxId);
    const modalAlertMsg = document.getElementById(modalAlertMessageId);
    
    if (modalAlert && modalAlertMsg) {
      modalAlertMsg.textContent = message;
      modalAlert.classList.remove("d-none");
    }
  }
  
  /**
   * Esconde mensagem de erro no modal
   */
  function hideModalError(modalAlertBoxId = "modalAlertBox") {
    const modalAlert = document.getElementById(modalAlertBoxId);
    if (modalAlert) {
      modalAlert.classList.add("d-none");
    }
  }