import { HttpErrorResponse } from '@angular/common/http';

import { mensagemDeErro } from './mensagem-erro';

describe('mensagemDeErro', () => {
  it('usa a mensagem do corpo de erro da API', () => {
    const erro = new HttpErrorResponse({
      status: 409,
      error: { erro: 'ESTOQUE_INSUFICIENTE', mensagem: 'Estoque insuficiente: solicitado 100, disponível 77.' },
    });

    expect(mensagemDeErro(erro)).toBe('Estoque insuficiente: solicitado 100, disponível 77.');
  });

  it('avisa quando a API está fora do ar', () => {
    expect(mensagemDeErro(new HttpErrorResponse({ status: 0 }))).toContain('Não foi possível conectar');
  });

  it('cai numa mensagem genérica quando o corpo não tem o formato esperado', () => {
    expect(mensagemDeErro(new HttpErrorResponse({ status: 502, error: '<html>' }))).toBe(
      'Erro 502 inesperado.',
    );
  });

  it('trata erros que não são HTTP', () => {
    expect(mensagemDeErro(new Error('x'))).toBe('Erro inesperado.');
  });
});
