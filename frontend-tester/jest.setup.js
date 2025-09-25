import 'whatwg-fetch';
import '@testing-library/jest-dom';

// Mock do módulo firebase.ts
jest.mock('lib/firebase', () => ({
  auth: {
    onAuthStateChanged: jest.fn((callback) => {
      // Simula nenhum usuário logado por padrão para testes
      callback(null);
      return jest.fn(); // Retorna uma função de unsubscribe
    }),
    signOut: jest.fn(() => Promise.resolve()),
    // Mock de outros métodos de auth conforme necessário
  },
  // Mock de outros exports de firebase.ts se houver
}));

// Mock do módulo AuthContext.tsx
jest.mock('src/context/AuthContext', () => ({
  useAuth: jest.fn(() => ({
    currentUser: { uid: 'test-uid', email: 'test@example.com' },
    idToken: 'mock-id-token',
    loading: false,
    signIn: jest.fn(),
    signUp: jest.fn(),
    signOut: jest.fn(),
  })),
  AuthProvider: ({ children }) => children, // Simplificado
  AuthContext: { // Mock do objeto AuthContext para que .Provider não seja undefined
    Provider: ({ children }) => children, // Simplificado
  },
}));

// Mock do useRouter do Next.js
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: jest.fn(),
    replace: jest.fn(),
    reload: jest.fn(),
    back: jest.fn(),
    prefetch: jest.fn(),
    beforePopState: jest.fn(),
    events: {
      on: jest.fn(),
      off: jest.fn(),
      emit: jest.fn(),
    },
  })),
  usePathname: jest.fn(() => '/'), // Mock para retornar um pathname padrão
  useSearchParams: jest.fn(() => new URLSearchParams()),
}));
