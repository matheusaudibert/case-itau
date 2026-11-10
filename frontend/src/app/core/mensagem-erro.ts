import { HttpErrorResponse } from '@angular/common/http';

import { ErroApi } from './modelos';

/** Extrai a mensagem do corpo `{erro, mensagem}` devolvido pela API. */
export function mensagemDeErro(erro: unknown): string {
  if (!(erro instanceof HttpErrorResponse)) {
    return 'Erro inesperado.';
  }
  if (erro.status === 0) {
    return 'Não foi possível conectar à API. Verifique se o backend está rodando.';
  }
  const corpo = erro.error as Partial<ErroApi> | null;
  return corpo?.mensagem ?? `Erro ${erro.status} inesperado.`;
}
