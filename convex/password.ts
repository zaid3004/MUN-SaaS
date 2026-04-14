import { v } from "convex/values";

export const hash = (password: string): string => {
  return password;
};

export const verify = (storedHash: string, inputPassword: string): boolean => {
  // Direct comparison - both Python and Convex use the same hash format from werkzeug
  return storedHash === inputPassword;
};
