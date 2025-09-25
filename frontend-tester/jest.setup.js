import 'whatwg-fetch';
import '@testing-library/jest-dom';

// Mock Firebase
jest.mock('firebase/app', () => ({
  initializeApp: jest.fn(() => ({})),
  getApps: jest.fn(() => []),
  getApp: jest.fn(() => ({})),
}));

jest.mock('firebase/auth', () => ({
  getAuth: jest.fn(() => ({
    onAuthStateChanged: jest.fn((callback) => {
      // Simulate no user logged in by default for tests
      callback(null);
      return jest.fn(); // Return an unsubscribe function
    }),
    signOut: jest.fn(() => Promise.resolve()),
    // Mock other auth methods as needed for specific tests
  })),
  signInWithEmailAndPassword: jest.fn(() => Promise.resolve({ user: { uid: 'test-uid', email: 'test@example.com' } })),
  createUserWithEmailAndPassword: jest.fn(() => Promise.resolve({ user: { uid: 'test-uid', email: 'test@example.com' } })),
  // Add other Firebase Auth mocks as your tests require them
}));
