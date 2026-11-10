import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { Bloqueio, Produto, Reserva, Status } from './modelos';

/** Cliente das rotas da API. Não valida regras: quem decide é o backend. */
@Injectable({ providedIn: 'root' })
export class EstoqueApi {
  private readonly http = inject(HttpClient);
  private readonly url = environment.apiUrl;

  listarProdutos(): Observable<Produto[]> {
    return this.http.get<Produto[]>(`${this.url}/produtos`);
  }

  consultarProduto(produtoId: string): Observable<Produto> {
    return this.http.get<Produto>(`${this.url}/produtos/${encodeURIComponent(produtoId)}`);
  }

  criarProduto(id: string, nome: string): Observable<Produto> {
    return this.http.post<Produto>(`${this.url}/produtos`, { id, nome });
  }

  entrada(produtoId: string, quantidade: number): Observable<Produto> {
    return this.http.post<Produto>(`${this.urlProduto(produtoId)}/entradas`, { quantidade });
  }

  saida(produtoId: string, quantidade: number): Observable<Produto> {
    return this.http.post<Produto>(`${this.urlProduto(produtoId)}/saidas`, { quantidade });
  }

  reservar(produtoId: string, quantidade: number, motivo: string | null): Observable<Reserva> {
    return this.http.post<Reserva>(`${this.urlProduto(produtoId)}/reservas`, {
      quantidade,
      motivo,
    });
  }

  bloquear(produtoId: string, quantidade: number, motivo: string | null): Observable<Bloqueio> {
    return this.http.post<Bloqueio>(`${this.urlProduto(produtoId)}/bloqueios`, {
      quantidade,
      motivo,
    });
  }

  listarReservas(produtoId: string, status?: Status): Observable<Reserva[]> {
    return this.http.get<Reserva[]>(`${this.urlProduto(produtoId)}/reservas`, {
      params: filtroStatus(status),
    });
  }

  listarBloqueios(produtoId: string, status?: Status): Observable<Bloqueio[]> {
    return this.http.get<Bloqueio[]>(`${this.urlProduto(produtoId)}/bloqueios`, {
      params: filtroStatus(status),
    });
  }

  consultarReserva(reservaId: string): Observable<Reserva> {
    return this.http.get<Reserva>(`${this.url}/reservas/${encodeURIComponent(reservaId)}`);
  }

  consultarBloqueio(bloqueioId: string): Observable<Bloqueio> {
    return this.http.get<Bloqueio>(`${this.url}/bloqueios/${encodeURIComponent(bloqueioId)}`);
  }

  liberarReserva(reservaId: string): Observable<Reserva> {
    return this.http.post<Reserva>(
      `${this.url}/reservas/${encodeURIComponent(reservaId)}/liberar`,
      null,
    );
  }

  liberarBloqueio(bloqueioId: string): Observable<Bloqueio> {
    return this.http.post<Bloqueio>(
      `${this.url}/bloqueios/${encodeURIComponent(bloqueioId)}/liberar`,
      null,
    );
  }

  private urlProduto(produtoId: string): string {
    return `${this.url}/produtos/${encodeURIComponent(produtoId)}`;
  }
}

function filtroStatus(status?: Status): HttpParams {
  return status ? new HttpParams().set('status', status) : new HttpParams();
}
