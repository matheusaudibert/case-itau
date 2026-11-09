import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../environments/environment';
import { EstoqueApi } from './estoque-api';

describe('EstoqueApi', () => {
  const url = environment.apiUrl;
  let api: EstoqueApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(EstoqueApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const casos: [string, () => unknown, string, string, unknown][] = [
    ['listarProdutos', () => api.listarProdutos(), 'GET', '/produtos', null],
    ['consultarProduto', () => api.consultarProduto('P001'), 'GET', '/produtos/P001', null],
    ['criarProduto', () => api.criarProduto('P003', 'Monitor'), 'POST', '/produtos', { id: 'P003', nome: 'Monitor' }],
    ['entrada', () => api.entrada('P001', 5), 'POST', '/produtos/P001/entradas', { quantidade: 5 }],
    ['saida', () => api.saida('P001', 2), 'POST', '/produtos/P001/saidas', { quantidade: 2 }],
    [
      'reservar',
      () => api.reservar('P001', 3, 'Reserva para Matheus'),
      'POST',
      '/produtos/P001/reservas',
      { quantidade: 3, motivo: 'Reserva para Matheus' },
    ],
    [
      'bloquear',
      () => api.bloquear('P001', 1, null),
      'POST',
      '/produtos/P001/bloqueios',
      { quantidade: 1, motivo: null },
    ],
    ['listarReservas', () => api.listarReservas('P001'), 'GET', '/produtos/P001/reservas', null],
    [
      'listarReservas com status',
      () => api.listarReservas('P001', 'ATIVO'),
      'GET',
      '/produtos/P001/reservas?status=ATIVO',
      null,
    ],
    [
      'listarBloqueios com status',
      () => api.listarBloqueios('P001', 'LIBERADO'),
      'GET',
      '/produtos/P001/bloqueios?status=LIBERADO',
      null,
    ],
    ['consultarReserva', () => api.consultarReserva('abc'), 'GET', '/reservas/abc', null],
    ['consultarBloqueio', () => api.consultarBloqueio('abc'), 'GET', '/bloqueios/abc', null],
    ['liberarReserva', () => api.liberarReserva('abc'), 'POST', '/reservas/abc/liberar', null],
    ['liberarBloqueio', () => api.liberarBloqueio('abc'), 'POST', '/bloqueios/abc/liberar', null],
  ];

  it.each(casos)('%s chama a rota certa', (nome, chamar, metodo, caminho, corpo) => {
    (chamar() as { subscribe: () => void }).subscribe();

    const requisicao = http.expectOne(`${url}${caminho}`);
    expect(requisicao.request.method).toBe(metodo);
    expect(requisicao.request.body).toEqual(corpo);
    requisicao.flush({});
  });

  it('codifica o id do produto na URL', () => {
    api.consultarProduto('P 001').subscribe();

    http.expectOne(`${url}/produtos/P%20001`).flush({});
  });
});
