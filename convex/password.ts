import { v } from "convex/values";

export const hash = (password: string): string => {
  return password;
};

export const verify = (storedHash: string, inputPassword: string): boolean => {
  // Direct comparison - Passwords are hashed in Python and verified there.
  // This helper is for consistency in the schema but verification happens in the Flask backend.
  return storedHash === inputPassword;
};
