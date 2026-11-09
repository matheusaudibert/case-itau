import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { RouterLink } from '@angular/router';
import { Observable } from 'rxjs';

import { EstoqueApi } from '../core/estoque-api';
import { Bloqueio, Reserva } from '../core/modelos';
import { Notificacao } from '../core/notificacao';

type Tipo = 'reserva' | 'bloqueio';
type Resultado = { tipo: 'reserva'; registro: Reserva } | { tipo: 'bloqueio'; registro: Bloqueio };

@Component({
  selector: 'app-consulta',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
  ],
  templateUrl: './consulta.html',
  styleUrl: './consulta.scss',
})
export class Consulta {
  private readonly api = inject(EstoqueApi);
  private readonly notificacao = inject(Notificacao);

  protected readonly tipo = signal<Tipo>('reserva');
  protected readonly resultado = signal<Resultado | null>(null);
  protected readonly enviando = signal(false);
  protected readonly form = inject(FormBuilder).nonNullable.group({
    id: ['', Validators.required],
  });

  protected trocarTipo(tipo: Tipo): void {
    this.tipo.set(tipo);
    this.resultado.set(null);
  }

  protected consultar(): void {
    const id = this.form.getRawValue().id.trim();
    const tipo = this.tipo();
    const chamada: Observable<Reserva | Bloqueio> =
      tipo === 'reserva' ? this.api.consultarReserva(id) : this.api.consultarBloqueio(id);
    this.executar(chamada, tipo);
  }

  protected liberar(): void {
    const atual = this.resultado();
    if (!atual) {
      return;
    }
    const chamada: Observable<Reserva | Bloqueio> =
      atual.tipo === 'reserva'
        ? this.api.liberarReserva(atual.registro.id)
        : this.api.liberarBloqueio(atual.registro.id);
    this.executar(chamada, atual.tipo, atual.tipo === 'reserva' ? 'Reserva liberada.' : 'Bloqueio liberado.');
  }

  private executar(chamada: Observable<Reserva | Bloqueio>, tipo: Tipo, sucesso?: string): void {
    this.enviando.set(true);
    chamada.subscribe({
      next: (registro) => {
        this.resultado.set({ tipo, registro } as Resultado);
        if (sucesso) {
          this.notificacao.sucesso(sucesso);
        }
        this.enviando.set(false);
      },
      error: (erro) => {
        this.notificacao.erro(erro);
        if (!sucesso) {
          this.resultado.set(null);
        }
        this.enviando.set(false);
      },
    });
  }
}
