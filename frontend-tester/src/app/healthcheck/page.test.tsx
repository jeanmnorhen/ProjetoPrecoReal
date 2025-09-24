
import { render, screen, waitFor } from '@testing-library/react';
import HealthcheckPage from './page';
import '@testing-library/jest-dom';

// Mock do process.env para simular a variável de ambiente
const mockHealthcheckApiUrl = "http://mock-healthcheck-api.com";
const originalEnv = process.env;

beforeEach(() => {
  jest.clearAllMocks();
  process.env = {
    ...originalEnv,
    NEXT_PUBLIC_HEALTHCHECK_API_URL: mockHealthcheckApiUrl,
  };
});

afterEach(() => {
  process.env = originalEnv; // Restaura o ambiente original
});

describe('HealthcheckPage', () => {
  it('should display loading status initially', () => {
    render(<HealthcheckPage />);
    expect(screen.getByText('Verificando status do serviço...')).toBeInTheDocument();
  });

  it('should display operational status on successful API call', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'operational' }),
      })
    ) as jest.Mock;

    render(<HealthcheckPage />);

    await waitFor(() => {
      expect(screen.getByText('Serviço de Healthcheck está operacional!')).toBeInTheDocument();
    });
    expect(screen.queryByText('Verificando status do serviço...')).not.toBeInTheDocument();
  });

  it('should display error status on failed API call', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ error: 'Service unavailable' }),
      })
    ) as jest.Mock;

    render(<HealthcheckPage />);

    await waitFor(() => {
      expect(screen.getByText('Erro ao verificar o status do serviço: Service unavailable')).toBeInTheDocument();
    });
    expect(screen.queryByText('Verificando status do serviço...')).not.toBeInTheDocument();
  });

  it('should display error when NEXT_PUBLIC_HEALTHCHECK_API_URL is not configured', async () => {
    process.env.NEXT_PUBLIC_HEALTHCHECK_API_URL = undefined;

    render(<HealthcheckPage />);

    await waitFor(() => {
      expect(screen.getByText('Erro: URL da API de Healthcheck não configurada.')).toBeInTheDocument();
    });
    expect(screen.queryByText('Verificando status do serviço...')).not.toBeInTheDocument();
  });
});
