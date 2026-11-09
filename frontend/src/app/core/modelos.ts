export type Status = 'ATIVO' | 'LIBERADO';

export interface Produto {
  id: string;
  nome: string;
  total: number;
  disponivel: number;
  reservado: number;
  bloqueado: number;
}

export interface Reserva {
  id: string;
  produto_id: string;
  quantidade: number;
  motivo: string | null;
  status: Status;
  criado_em: string;
  liberado_em: string | null;
}

export interface Bloqueio {
  id: string;
  produto_id: string;
  quantidade: number;
  motivo: string | null;
  status: Status;
  criado_em: string;
  liberado_em: string | null;
}

export interface ErroApi {
  erro: string;
  mensagem: string;
}
