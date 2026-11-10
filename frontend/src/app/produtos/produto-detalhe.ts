import { Component, OnInit, inject, input, signal, viewChild } from '@angular/core';
import { FormBuilder, FormGroupDirective, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { RouterLink } from '@angular/router';
import { Observable, forkJoin } from 'rxjs';

import { EstoqueApi } from '../core/estoque-api';
import { Bloqueio, Produto, Reserva, Status } from '../core/modelos';
import { Notificacao } from '../core/notificacao';
import { TabelaRegistros } from './tabela-registros';

type Operacao = 'entrada' | 'saida' | 'reservar' | 'bloquear';
type FiltroStatus = Status | 'TODOS';

@Component({
  selector: 'app-produto-detalhe',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatTabsModule,
    TabelaRegistros,
  ],
  templateUrl: './produto-detalhe.html',
  styleUrl: './produto-detalhe.scss',
})
export class ProdutoDetalhe implements OnInit {
  private readonly api = inject(EstoqueApi);
  private readonly notificacao = inject(Notificacao);

  /** Vem do parâmetro `:produtoId` da rota. */
  readonly produtoId = input.required<string>();

  protected readonly produto = signal<Produto | null>(null);
  protected readonly reservas = signal<Reserva[]>([]);
  protected readonly bloqueios = signal<Bloqueio[]>([]);
  protected readonly filtroReservas = signal<FiltroStatus>('TODOS');
  protected readonly filtroBloqueios = signal<FiltroStatus>('TODOS');
  protected readonly carregando = signal(false);
  protected readonly enviando = signal(false);
  protected readonly naoEncontrado = signal(false);

  protected readonly operacao = signal<Operacao>('entrada');
  /** `resetForm()` da diretiva também limpa o estado "enviado"; `form.reset()` deixaria o campo marcado como erro. */
  private readonly formulario = viewChild(FormGroupDirective);
  protected readonly form = inject(FormBuilder).group({
    quantidade: [null as number | null, Validators.required],
    motivo: [''],
  });

  ngOnInit(): void {
    this.carregarTudo();
  }

  protected carregarTudo(): void {
    this.carregando.set(true);
    forkJoin({
      produto: this.api.consultarProduto(this.produtoId()),
      reservas: this.api.listarReservas(this.produtoId(), statusDoFiltro(this.filtroReservas())),
      bloqueios: this.api.listarBloqueios(this.produtoId(), statusDoFiltro(this.filtroBloqueios())),
    }).subscribe({
      next: ({ produto, reservas, bloqueios }) => {
        this.produto.set(produto);
        this.reservas.set(reservas);
        this.bloqueios.set(bloqueios);
        this.naoEncontrado.set(false);
        this.carregando.set(false);
      },
      error: (erro) => {
        this.naoEncontrado.set(erro?.status === 404);
        this.notificacao.erro(erro);
        this.carregando.set(false);
      },
    });
  }

  protected filtrarReservas(filtro: FiltroStatus): void {
    this.filtroReservas.set(filtro);
    this.api.listarReservas(this.produtoId(), statusDoFiltro(filtro)).subscribe({
      next: (reservas) => this.reservas.set(reservas),
      error: (erro) => this.notificacao.erro(erro),
    });
  }

  protected filtrarBloqueios(filtro: FiltroStatus): void {
    this.filtroBloqueios.set(filtro);
    this.api.listarBloqueios(this.produtoId(), statusDoFiltro(filtro)).subscribe({
      next: (bloqueios) => this.bloqueios.set(bloqueios),
      error: (erro) => this.notificacao.erro(erro),
    });
  }

  protected podeEnviar(): boolean {
    return this.form.valid && !this.enviando();
  }

  protected enviar(): void {
    const { quantidade, motivo } = this.form.getRawValue();
    const id = this.produtoId();
    const operacao = this.operacao();
    const chamadas: Record<Operacao, () => Observable<unknown>> = {
      entrada: () => this.api.entrada(id, quantidade!),
      saida: () => this.api.saida(id, quantidade!),
      reservar: () => this.api.reservar(id, quantidade!, motivo || null),
      bloquear: () => this.api.bloquear(id, quantidade!, motivo || null),
    };
    const mensagens: Record<Operacao, string> = {
      entrada: `Entrada de ${quantidade} registrada.`,
      saida: `Saída de ${quantidade} registrada.`,
      reservar: `Reserva de ${quantidade} criada.`,
      bloquear: `Bloqueio de ${quantidade} criado.`,
    };

    this.enviando.set(true);
    chamadas[operacao]().subscribe({
      next: () => {
        this.notificacao.sucesso(mensagens[operacao]);
        this.formulario()?.resetForm();
        this.enviando.set(false);
        this.carregarTudo();
      },
      error: (erro) => {
        this.notificacao.erro(erro);
        this.enviando.set(false);
      },
    });
  }

  protected liberarReserva(reservaId: string): void {
    this.liberar(this.api.liberarReserva(reservaId), 'Reserva liberada.');
  }

  protected liberarBloqueio(bloqueioId: string): void {
    this.liberar(this.api.liberarBloqueio(bloqueioId), 'Bloqueio liberado.');
  }

  private liberar(chamada: Observable<unknown>, mensagem: string): void {
    this.enviando.set(true);
    chamada.subscribe({
      next: () => {
        this.notificacao.sucesso(mensagem);
        this.enviando.set(false);
        this.carregarTudo();
      },
      error: (erro) => {
        this.notificacao.erro(erro);
        this.enviando.set(false);
        this.carregarTudo();
      },
    });
  }
}

function statusDoFiltro(filtro: FiltroStatus): Status | undefined {
  return filtro === 'TODOS' ? undefined : filtro;
}
