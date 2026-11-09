import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { EstoqueApi } from '../core/estoque-api';
import { mensagemDeErro } from '../core/mensagem-erro';
import { Produto } from '../core/modelos';

/** Cria o produto pela API; o erro (id inválido, já existente...) aparece no próprio diálogo. */
@Component({
  selector: 'app-novo-produto-dialog',
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule],
  template: `
    <h2 mat-dialog-title>Novo produto</h2>
    <form [formGroup]="form" (ngSubmit)="salvar()">
      <mat-dialog-content>
        <mat-form-field appearance="outline">
          <mat-label>Id</mat-label>
          <input matInput formControlName="id" placeholder="P003" autocomplete="off" />
          <mat-hint>Formato: P seguido de 3 dígitos</mat-hint>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Nome</mat-label>
          <input matInput formControlName="nome" autocomplete="off" />
        </mat-form-field>
        @if (erro()) {
          <p class="erro" role="alert">{{ erro() }}</p>
        }
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancelar</button>
        <button mat-flat-button type="submit" [disabled]="form.invalid || salvando()">Criar</button>
      </mat-dialog-actions>
    </form>
  `,
  styles: `
    mat-form-field {
      display: block;
      margin-bottom: 8px;
    }
    .erro {
      color: var(--mat-sys-error);
      margin: 0;
    }
  `,
})
export class NovoProdutoDialog {
  private readonly api = inject(EstoqueApi);
  private readonly dialogRef = inject<MatDialogRef<NovoProdutoDialog, Produto>>(MatDialogRef);

  protected readonly form = inject(FormBuilder).nonNullable.group({
    id: ['', Validators.required],
    nome: ['', Validators.required],
  });
  protected readonly salvando = signal(false);
  protected readonly erro = signal<string | null>(null);

  protected salvar(): void {
    const { id, nome } = this.form.getRawValue();
    this.salvando.set(true);
    this.erro.set(null);
    this.api.criarProduto(id, nome).subscribe({
      next: (produto) => this.dialogRef.close(produto),
      error: (erro) => {
        this.erro.set(mensagemDeErro(erro));
        this.salvando.set(false);
      },
    });
  }
}
