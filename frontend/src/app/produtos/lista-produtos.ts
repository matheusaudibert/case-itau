import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterLink } from '@angular/router';

import { EstoqueApi } from '../core/estoque-api';
import { Produto } from '../core/modelos';
import { Notificacao } from '../core/notificacao';
import { NovoProdutoDialog } from './novo-produto-dialog';

@Component({
  selector: 'app-lista-produtos',
  imports: [
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './lista-produtos.html',
  styleUrl: './lista-produtos.scss',
})
export class ListaProdutos implements OnInit {
  private readonly api = inject(EstoqueApi);
  private readonly notificacao = inject(Notificacao);
  private readonly dialog = inject(MatDialog);
  private readonly router = inject(Router);

  protected readonly colunas = ['id', 'nome', 'total', 'disponivel', 'reservado', 'bloqueado'];
  protected readonly produtos = signal<Produto[]>([]);
  protected readonly carregando = signal(false);

  ngOnInit(): void {
    this.carregar();
  }

  protected carregar(): void {
    this.carregando.set(true);
    this.api.listarProdutos().subscribe({
      next: (produtos) => {
        this.produtos.set(produtos);
        this.carregando.set(false);
      },
      error: (erro) => {
        this.notificacao.erro(erro);
        this.carregando.set(false);
      },
    });
  }

  protected abrirNovoProduto(): void {
    this.dialog
      .open(NovoProdutoDialog, { width: '420px' })
      .afterClosed()
      .subscribe((criado: Produto | undefined) => {
        if (criado) {
          this.notificacao.sucesso(`Produto ${criado.id} criado.`);
          this.carregar();
        }
      });
  }

  protected abrir(produto: Produto): void {
    this.router.navigate(['/produtos', produto.id]);
  }
}
