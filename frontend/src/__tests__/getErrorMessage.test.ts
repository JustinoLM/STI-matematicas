import { AxiosError } from 'axios';
import { describe, expect, it } from 'vitest';
import { getErrorMessage } from '@/services/api';

function errorAxios(code?: string, data?: unknown, status?: number) {
  const err = new AxiosError('fallo', code);
  if (status) {
    err.response = { data, status, statusText: '', headers: {}, config: {} as never };
  }
  return err;
}

describe('getErrorMessage', () => {
  it('une los mensajes de un error 422 de FastAPI (detail como lista)', () => {
    const err = errorAxios(undefined, { detail: [{ msg: 'campo requerido' }, {}] }, 422);
    expect(getErrorMessage(err)).toBe('campo requerido, Error de validación');
  });

  it('devuelve el detail cuando es texto', () => {
    expect(getErrorMessage(errorAxios(undefined, { detail: 'Credenciales inválidas' }, 401))).toBe(
      'Credenciales inválidas'
    );
  });

  it('explica el tiempo agotado y la falta de conexión', () => {
    expect(getErrorMessage(errorAxios('ECONNABORTED'))).toMatch(/tardó demasiado/);
    expect(getErrorMessage(errorAxios('ERR_NETWORK'))).toMatch(/No se pudo conectar/);
  });

  it('usa el mensaje de errores no axios y un texto por defecto', () => {
    expect(getErrorMessage(new Error('boom'))).toBe('boom');
    expect(getErrorMessage('x')).toBe('Error desconocido');
  });
});
