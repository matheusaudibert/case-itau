import { DatePipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { Bloqueio, Reserva } from '../core/modelos';

type Registro = Reserva | Bloqueio;

/** Tabela de reservas ou bloqueios, com o botão de liberar nos ativos. */
@Component({
  selector: 'app-tabela-registros',
  imports: [DatePipe, MatButtonModule, MatChipsModule, MatIconModule, MatTableModule, MatTooltipModule],
  template: `
    <table mat-table [dataSource]="registros()">
      <ng-container matColumnDef="id">
        <th mat-header-cell *matHeaderCellDef>Id</th>
        <td mat-cell *matCellDef="let r">
          <code [matTooltip]="r.id">{{ r.id.slice(0, 8) }}…</code>
        </td>
      </ng-container>

      <ng-container matColumnDef="motivo">
        <th mat-header-cell *matHeaderCellDef>Motivo</th>
        <td mat-cell *matCellDef="let r">{{ r.motivo || '—' }}</td>
      </ng-container>

      <ng-container matColumnDef="quantidade">
        <th mat-header-cell *matHeaderCellDef class="numero">Quantidade</th>
        <td mat-cell *matCellDef="let r" class="numero">{{ r.quantidade }}</td>
      </ng-container>

      <ng-container matColumnDef="status">
        <th mat-header-cell *matHeaderCellDef>Status</th>
        <td mat-cell *matCellDef="let r">
          <span class="status" [class.ativo]="r.status === 'ATIVO'">{{ r.status }}</span>
        </td>
      </ng-container>

      <ng-container matColumnDef="criado_em">
        <th mat-header-cell *matHeaderCellDef>Criado em</th>
        <td mat-cell *matCellDef="let r">{{ r.criado_em | date: 'dd/MM/yyyy HH:mm:ss' }}</td>
      </ng-container>

      <ng-container matColumnDef="liberado_em">
        <th mat-header-cell *matHeaderCellDef>Liberado em</th>
        <td mat-cell *matCellDef="let r">
          {{ r.liberado_em ? (r.liberado_em | date: 'dd/MM/yyyy HH:mm:ss') : '—' }}
        </td>
      </ng-container>

      <ng-container matColumnDef="acoes">
        <th mat-header-cell *matHeaderCellDef></th>
        <td mat-cell *matCellDef="let r" class="acoes">
          @if (r.status === 'ATIVO') {
            <button mat-stroked-button [disabled]="desabilitado()" (click)="liberar.emit(r.id)">
              <mat-icon>lock_open</mat-icon>
              Liberar
            </button>
          }
        </td>
      </ng-container>

      <tr mat-header-row *matHeaderRowDef="colunas"></tr>
      <tr mat-row *matRowDef="let r; columns: colunas"></tr>
      <tr class="mat-row" *matNoDataRow>
        <td class="vazio" [attr.colspan]="colunas.length">{{ mensagemVazia() }}</td>
      </tr>
    </table>
  `,
  styles: `
    table {
      width: 100%;
    }
    .numero {
      text-align: right;
    }
    .acoes {
      text-align: right;
    }
    code {
      font-size: 12px;
    }
    .status {
      padding: 2px 8px;
      border-radius: 12px;
      font: var(--mat-sys-label-small);
      background-color: var(--mat-sys-surface-container-highest);
      color: var(--mat-sys-on-surface-variant);
    }
    .status.ativo {
      background-color: var(--mat-sys-primary-container);
      color: var(--mat-sys-on-primary-container);
    }
    .vazio {
      padding: 24px;
      text-align: center;
      color: var(--mat-sys-on-surface-variant);
    }
  `,
})
export class TabelaRegistros {
  readonly registros = input.required<Registro[]>();
  readonly mensagemVazia = input('Nenhum registro.');
  readonly desabilitado = input(false);
  readonly liberar = output<string>();

  protected readonly colunas = [
    'id',
    'motivo',
    'quantidade',
    'status',
    'criado_em',
    'liberado_em',
    'acoes',
  ];
}
