
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import HealthcheckPage from './page';
import '@testing-library/jest-dom';

// Mock do useAuth para simular um usuário admin autenticado
jest.mock('../../context/AuthContext', () => ({
  useAuth: () => ({
    currentUser: { uid: 'test-admin-uid' }, // Simula um usuário logado
    isAdmin: true, // Simula que o usuário é admin
    loading: false, // Simula que a autenticação não está carregando
  }),
}));

// Mock do process.env para simular a variável de ambiente
const mockHealthcheckApiUrl = "http://mock-healthcheck-api.com";
const originalEnv = process.env;

beforeEach(() => {
  jest.clearAllMocks();
  process.env = {
    ...originalEnv,
    NEXT_PUBLIC_HEALTHCHECK_API_URL: mockHealthcheckApiUrl,
  };
  // Reset fetch mock before each test
  global.fetch = jest.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({}),
      ok: true,
      status: 200,
    })
  ) as jest.Mock;
});

afterEach(() => {
  process.env = originalEnv; // Restaura o ambiente original
});

describe('HealthcheckPage', () => {
  it('should display loading status initially', async () => {
    let resolveFetch: (value: any) => void;
    global.fetch = jest.fn(() => new Promise(resolve => { resolveFetch = resolve; })) as jest.Mock;

    await act(async () => {
      render(<HealthcheckPage />);
    });
    expect(screen.getByText('Loading health check...')).toBeInTheDocument();

    // Resolve the fetch promise to allow the component to move past loading state
    await act(async () => {
      resolveFetch({ ok: true, json: () => Promise.resolve({ status: 'operational' }), status: 200 });
    });

    await waitFor(() => {
      expect(screen.queryByText('Carregando health check...')).not.toBeInTheDocument();
    });
  });

  it('should display operational status on successful API call', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'operational' }),
        status: 200, // Ensure status is set for successful response
      })
    ) as jest.Mock;

    await act(async () => {
      render(<HealthcheckPage />);
    });

    await waitFor(() => {
      expect(screen.getByText(/"status": "operational"/i)).toBeInTheDocument();
    });
    expect(screen.queryByText('Carregando health check...')).not.toBeInTheDocument();
  });

  it('should display error status on failed API call', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ error: 'Service unavailable' }),
        status: 500, // Simulate a 500 error
      })
    ) as jest.Mock;

    await act(async () => {
      render(<HealthcheckPage />);
    });

    await waitFor(() => {
      expect(screen.getByText('Error: HTTP error! status: 500')).toBeInTheDocument();
    });
    expect(screen.queryByText('Carregando health check...')).not.toBeInTheDocument();
  });

  it('should display error when NEXT_PUBLIC_HEALTHCHECK_API_URL is not configured', async () => {
    process.env.NEXT_PUBLIC_HEALTHCHECK_API_URL = undefined;

    await act(async () => {
      render(<HealthcheckPage />);
    });

    await waitFor(() => {
      expect(screen.getByText('Error: URL da API de Healthcheck não configurada.')).toBeInTheDocument();
    });
    expect(screen.queryByText('Carregando health check...')).not.toBeInTheDocument();
  });
});
