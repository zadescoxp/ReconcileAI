// Authentication types based on design document

export enum Role {
  ADMIN = "Admin",
  USER = "User"
}

export interface User {
  userId: string;
  username: string;
  email: string;
  role: Role;
}

export interface AuthResult {
  user: User;
  accessToken: string;
  idToken: string;
}
