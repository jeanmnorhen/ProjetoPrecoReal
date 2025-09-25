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