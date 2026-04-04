const LOGIN_ID_PATTERN = /^[a-z0-9._@-]+$/;
const UPI_HANDLE_PATTERN = /^[^@\s]+@[^@\s]+$/;
const DIGITS_ONLY_PATTERN = /^\d{10}$/;

const normalizeText = (value) => (typeof value === "string" ? value.trim() : "");

export const hasValidationErrors = (errors) => Object.values(errors).some(Boolean);

export const validateRegisterField = (name, value, zones = []) => {
  const trimmedValue = normalizeText(value);

  switch (name) {
    case "login_id": {
      const cleaned = trimmedValue.toLowerCase();
      if (!cleaned) return "Login ID is required.";
      if (cleaned.length < 4) return "Login ID must be at least 4 characters.";
      if (!LOGIN_ID_PATTERN.test(cleaned)) {
        return "Login ID may only contain letters, numbers, ., _, -, and @.";
      }
      return "";
    }
    case "password":
      if (!value) return "Password is required.";
      if (value.length < 8) return "Password must be at least 8 characters.";
      if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) {
        return "Password must contain at least one letter and one number.";
      }
      return "";
    case "zomato_partner_id":
      return trimmedValue ? "" : "Zomato Partner ID is required.";
    case "name":
      return trimmedValue ? "" : "Full Name is required.";
    case "phone": {
      const digitsOnly = String(value || "").replace(/\D/g, "");
      if (!digitsOnly) return "Phone Number is required.";
      if (!DIGITS_ONLY_PATTERN.test(digitsOnly)) return "Phone Number must be exactly 10 digits.";
      return "";
    }
    case "zone":
      if (!trimmedValue) return "Primary Delivery Zone is required.";
      if (zones.length > 0 && !zones.includes(value)) return "Select a supported delivery zone.";
      return "";
    case "upi_handle": {
      const cleaned = trimmedValue.toLowerCase();
      if (!cleaned) return "UPI Handle is required.";
      if (!UPI_HANDLE_PATTERN.test(cleaned)) return "UPI Handle must look like name@bank.";
      return "";
    }
    default:
      return "";
  }
};

export const validateRegisterForm = (formData, zones = []) =>
  Object.keys(formData).reduce((errors, fieldName) => {
    errors[fieldName] = validateRegisterField(fieldName, formData[fieldName], zones);
    return errors;
  }, {});

export const validateAuthField = (name, value) => {
  const trimmedValue = normalizeText(value);

  switch (name) {
    case "login_id":
      return trimmedValue ? "" : "Login ID is required.";
    case "password":
      return value ? "" : "Password is required.";
    default:
      return "";
  }
};

export const validateAuthForm = (formData) =>
  Object.keys(formData).reduce((errors, fieldName) => {
    errors[fieldName] = validateAuthField(fieldName, formData[fieldName]);
    return errors;
  }, {});

export const mapRegisterApiMessageToFieldErrors = (message) => {
  switch (message) {
    case "Login ID already in use":
      return { login_id: message };
    case "Rider with this Zomato ID already exists":
      return { zomato_partner_id: message };
    case "Phone number must be 10 digits":
      return { phone: message };
    case "UPI handle must look like name@bank":
      return { upi_handle: message };
    case "Unsupported zone":
      return { zone: message };
    default:
      return {};
  }
};
