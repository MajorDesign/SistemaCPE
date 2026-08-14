# Endpoints da API

> Gerado automaticamente do `openapi.json` de produção — atualizar quando adicionar rotas relevantes.
> Total de endpoints:  **505** em **33** módulos.

Descrição detalhada dos módulos: ver `docs/MODULOS.md`.
Docs interativa (Swagger UI): `https://cpecontrol.cpetecnologia.com.br/api/docs`

---

## Sumário

- [agenda](#agenda) — 15 endpoints
- [Agents](#agents) — 3 endpoints
- [Atendimentos](#atendimentos) — 72 endpoints
- [auth](#auth) — 4 endpoints
- [AvaliaÃ§Ãµes](#avaliaã§ãµes) — 6 endpoints
- [categoria-campos](#categoria-campos) — 5 endpoints
- [categorias](#categorias) — 5 endpoints
- [chamados-antigos](#chamados-antigos) — 5 endpoints
- [chat](#chat) — 65 endpoints
- [Clicksign](#clicksign) — 1 endpoints
- [comercial](#comercial) — 18 endpoints
- [Contratos](#contratos) — 10 endpoints
- [dashboard](#dashboard) — 1 endpoints
- [email-preferencias](#email-preferencias) — 2 endpoints
- [Fleet](#fleet) — 58 endpoints
- [groups](#groups) — 9 endpoints
- [interacoes](#interacoes) — 2 endpoints
- [inventario](#inventario) — 38 endpoints
- [knowledge-base](#knowledge-base) — 9 endpoints
- [meetings](#meetings) — 13 endpoints
- [network](#network) — 7 endpoints
- [notificacoes](#notificacoes) — 5 endpoints
- [Passwords](#passwords) — 12 endpoints
- [Permissions](#permissions) — 9 endpoints
- [pre-cadastro](#pre-cadastro) — 12 endpoints
- [recepcao](#recepcao) — 25 endpoints
- [security](#security) — 2 endpoints
- [subcategorias](#subcategorias) — 4 endpoints
- [Tasks](#tasks) — 57 endpoints
- [tickets](#tickets) — 18 endpoints
- [unidades](#unidades) — 5 endpoints
- [untagged](#untagged) — 2 endpoints
- [users](#users) — 6 endpoints

---

## agenda

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/agenda/compartilhar/eventos/{dono_id}` | Eventos Compartilhados |
| `GET` | `/api/agenda/compartilhar/gerenciar` | Gerenciar Compartilhamentos |
| `GET` | `/api/agenda/compartilhar/meus` | Meus Compartilhamentos |
| `GET` | `/api/agenda/compartilhar/pendentes` | Compartilhamentos Pendentes |
| `POST` | `/api/agenda/compartilhar/solicitar` | Solicitar Compartilhamento |
| `DELETE` | `/api/agenda/compartilhar/{comp_id}` | Revogar Compartilhamento |
| `POST` | `/api/agenda/compartilhar/{comp_id}/responder` | Responder Compartilhamento |
| `GET` | `/api/agenda/eventos` | Eventos Agenda |
| `POST` | `/api/agenda/eventos` | Criar Evento Endpoint |
| `GET` | `/api/agenda/eventos/{evento_id}/detalhes` | Detalhes Evento |
| `POST` | `/api/agenda/eventos/{evento_id}/reenviar` | Reenviar Evento |
| `POST` | `/api/agenda/login` | Login Carbonio |
| `POST` | `/api/agenda/logout` | Logout Carbonio |
| `GET` | `/api/agenda/status` | Status Agenda |
| `GET` | `/api/agenda/usuarios/buscar` | Buscar Usuarios |

## Agents

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/agents` | List Agents |
| `POST` | `/api/agents/termo-notebook/submit` | Submit Termo Notebook |
| `GET` | `/api/agents/{agent_id}/download` | Download Agent |

## Atendimentos

| Método | Path | Descrição |
|---|---|---|
| `POST` | `/api/atendimentos/agendamentos` | Criar Agendamento |
| `GET` | `/api/atendimentos/agendamentos-do-dia` | Agendamentos Do Dia |
| `PUT` | `/api/atendimentos/agendamentos/{agendamento_id}` | Atualizar Agendamento |
| `DELETE` | `/api/atendimentos/agendamentos/{agendamento_id}` | Excluir Agendamento |
| `GET` | `/api/atendimentos/agendas` | Listar Agendas |
| `POST` | `/api/atendimentos/agendas` | Criar Agenda |
| `GET` | `/api/atendimentos/agendas/{agenda_id}` | Obter Agenda |
| `PUT` | `/api/atendimentos/agendas/{agenda_id}` | Atualizar Agenda |
| `DELETE` | `/api/atendimentos/agendas/{agenda_id}` | Excluir Agenda |
| `GET` | `/api/atendimentos/agendas/{agenda_id}/agendamentos` | Listar Agendamentos |
| `GET` | `/api/atendimentos/agendas/{agenda_id}/drones` | Listar Drones |
| `GET` | `/api/atendimentos/agendas/{agenda_id}/horarios` | Listar Horarios |
| `PUT` | `/api/atendimentos/agendas/{agenda_id}/horarios` | Salvar Horarios |
| `GET` | `/api/atendimentos/agendas/{agenda_id}/servicos` | Listar Servicos |
| `GET` | `/api/atendimentos/agendas/{agenda_id}/treinamentos` | Listar Treinamentos |
| `POST` | `/api/atendimentos/bloqueios` | Criar Bloqueio |
| `DELETE` | `/api/atendimentos/bloqueios/{bloqueio_id}` | Excluir Bloqueio |
| `GET` | `/api/atendimentos/clientes` | Listar Clientes |
| `PUT` | `/api/atendimentos/clientes` | Atualizar Cliente |
| `GET` | `/api/atendimentos/clientes/historico` | Historico Cliente |
| `GET` | `/api/atendimentos/dashboard` | Dashboard |
| `POST` | `/api/atendimentos/drones` | Criar Drone |
| `PUT` | `/api/atendimentos/drones/{drone_id}` | Atualizar Drone |
| `DELETE` | `/api/atendimentos/drones/{drone_id}` | Excluir Drone |
| `POST` | `/api/atendimentos/drones/{drone_id}/duplicar` | Duplicar Drone |
| `GET` | `/api/atendimentos/drones/{drone_id}/equipamentos` | Listar Equipamentos Drone |
| `GET` | `/api/atendimentos/equipamentos` | Listar Todos Equipamentos |
| `POST` | `/api/atendimentos/equipamentos` | Criar Equipamento |
| `PUT` | `/api/atendimentos/equipamentos/{equipamento_id}` | Atualizar Equipamento |
| `DELETE` | `/api/atendimentos/equipamentos/{equipamento_id}` | Excluir Equipamento |
| `POST` | `/api/atendimentos/equipamentos/{equipamento_id}/vinculos` | Add Vinculo Equipamento |
| `DELETE` | `/api/atendimentos/equipamentos/{equipamento_id}/vinculos` | Remover Vinculo Equipamento |
| `GET` | `/api/atendimentos/feriados` | Listar Feriados |
| `POST` | `/api/atendimentos/feriados` | Criar Feriado |
| `DELETE` | `/api/atendimentos/feriados/{feriado_id}` | Excluir Feriado |
| `GET` | `/api/atendimentos/instrutores-ociosidade` | Instrutores Ociosidade |
| `GET` | `/api/atendimentos/instrutores-suporte` | Listar Instrutores Suporte |
| `GET` | `/api/atendimentos/meu-nivel` | Meu Nivel |
| `DELETE` | `/api/atendimentos/midia/fotos/{foto_id}` | Excluir Foto |
| `DELETE` | `/api/atendimentos/midia/videos/{video_id}` | Excluir Video |
| `GET` | `/api/atendimentos/midia/{entidade}/{entidade_id}` | Listar Midia |
| `POST` | `/api/atendimentos/midia/{entidade}/{entidade_id}/banner` | Upload Banner |
| `DELETE` | `/api/atendimentos/midia/{entidade}/{entidade_id}/banner` | Excluir Banner |
| `POST` | `/api/atendimentos/midia/{entidade}/{entidade_id}/fotos` | Upload Foto |
| `POST` | `/api/atendimentos/midia/{entidade}/{entidade_id}/videos` | Adicionar Video |
| `PUT` | `/api/atendimentos/modulos/{modulo_id}` | Editar Modulo |
| `DELETE` | `/api/atendimentos/modulos/{modulo_id}` | Excluir Modulo |
| `GET` | `/api/atendimentos/pendentes` | Listar Pendentes |
| `GET` | `/api/atendimentos/pilotos` | Listar Pilotos |
| `POST` | `/api/atendimentos/publico/agendar` | Pub Agendar |
| `GET` | `/api/atendimentos/publico/agendas` | Pub Listar Agendas |
| `GET` | `/api/atendimentos/publico/agendas/{agenda_id}` | Pub Obter Agenda |
| `GET` | `/api/atendimentos/publico/agendas/{agenda_id}/dias` | Pub Dias Disponiveis |
| `GET` | `/api/atendimentos/publico/agendas/{agenda_id}/horarios` | Pub Horarios Disponiveis |
| `GET` | `/api/atendimentos/publico/drones/{drone_id}/equipamentos` | Pub Equipamentos Drone |
| `GET` | `/api/atendimentos/publico/servicos/{servico_id}/equipamentos` | Pub Equipamentos |
| `GET` | `/api/atendimentos/publico/treinamentos/{treinamento_id}/equipamentos` | Pub Equipamentos Treino |
| `GET` | `/api/atendimentos/publico/vendedores` | Pub Vendedores |
| `POST` | `/api/atendimentos/servicos` | Criar Servico |
| `PUT` | `/api/atendimentos/servicos/{servico_id}` | Atualizar Servico |
| `DELETE` | `/api/atendimentos/servicos/{servico_id}` | Excluir Servico |
| `POST` | `/api/atendimentos/servicos/{servico_id}/duplicar` | Duplicar Servico |
| `GET` | `/api/atendimentos/servicos/{servico_id}/equipamentos` | Listar Equipamentos |
| `POST` | `/api/atendimentos/treinamentos` | Criar Treinamento |
| `PUT` | `/api/atendimentos/treinamentos/{treinamento_id}` | Atualizar Treinamento |
| `DELETE` | `/api/atendimentos/treinamentos/{treinamento_id}` | Excluir Treinamento |
| `POST` | `/api/atendimentos/treinamentos/{treinamento_id}/duplicar` | Duplicar Treinamento |
| `GET` | `/api/atendimentos/treinamentos/{treinamento_id}/equipamentos` | Listar Equipamentos Treino |
| `GET` | `/api/atendimentos/vendedores` | Listar Vendedores |
| `GET` | `/api/atendimentos/{entidade}/{entidade_id}/modulos` | Listar Modulos |
| `POST` | `/api/atendimentos/{entidade}/{entidade_id}/modulos` | Criar Modulo |
| `POST` | `/api/atendimentos/{entidade}/{entidade_id}/modulos/reordenar` | Reordenar Modulos |

## auth

| Método | Path | Descrição |
|---|---|---|
| `POST` | `/api/auth/forgot-password` | Forgot Password |
| `POST` | `/api/auth/login` | Login |
| `POST` | `/api/auth/reset-password` | Reset Password |
| `GET` | `/api/auth/reset-password/validate` | Reset Password Validate |

## AvaliaÃ§Ãµes

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/avaliacoes` | Listar Avaliacoes |
| `GET` | `/api/avaliacoes/pendentes` | Avaliacoes Pendentes |
| `POST` | `/api/avaliacoes/popup-visto/{ticket_id}` | Registrar Popup Visto |
| `GET` | `/api/avaliacoes/por-responsavel` | Avaliacoes Por Responsavel |
| `GET` | `/api/avaliacoes/resumo` | Resumo Avaliacoes |
| `POST` | `/api/avaliacoes/{ticket_id}` | Submeter Avaliacao |

## categoria-campos

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/categoria-campos` | Listar Campos |
| `POST` | `/api/categoria-campos` | Criar Campo |
| `GET` | `/api/categoria-campos/do-ticket` | Campos Do Ticket |
| `PUT` | `/api/categoria-campos/{campo_id}` | Atualizar Campo |
| `DELETE` | `/api/categoria-campos/{campo_id}` | Excluir Campo |

## categorias

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/categorias/` | Listar Categorias |
| `POST` | `/api/categorias/` | Criar Categoria |
| `GET` | `/api/categorias/check-permissao` | Check Permissao Categorias |
| `PUT` | `/api/categorias/{categoria_id}` | Atualizar Categoria |
| `DELETE` | `/api/categorias/{categoria_id}` | Deletar Categoria |

## chamados-antigos

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/chamados-antigos` | Listar |
| `GET` | `/api/chamados-antigos/` | Listar |
| `GET` | `/api/chamados-antigos/categorias` | Listar Categorias |
| `GET` | `/api/chamados-antigos/stats` | Stats |
| `GET` | `/api/chamados-antigos/{trackid}` | Detalhe |

## chat

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/chat/_debug/online` | Debug Online |
| `POST` | `/api/chat/admin/cleanup-imagens` | Cleanup Imagens Antigas |
| `POST` | `/api/chat/admin/sync-grupos` | Sync Canais Grupos |
| `PATCH` | `/api/chat/categories/{category_id}` | Editar Categoria |
| `DELETE` | `/api/chat/categories/{category_id}` | Excluir Categoria |
| `GET` | `/api/chat/channels` | Listar Canais |
| `POST` | `/api/chat/channels` | Criar Canal |
| `POST` | `/api/chat/channels/dm/{other_user_id}` | Abrir Ou Criar Dm |
| `PATCH` | `/api/chat/channels/{channel_id}` | Editar Canal |
| `DELETE` | `/api/chat/channels/{channel_id}` | Arquivar Canal |
| `GET` | `/api/chat/channels/{channel_id}/members` | Listar Membros Enriquecido |
| `POST` | `/api/chat/channels/{channel_id}/members` | Adicionar Membros |
| `DELETE` | `/api/chat/channels/{channel_id}/members/{user_id}` | Remover Membro |
| `GET` | `/api/chat/channels/{channel_id}/messages` | Listar Mensagens |
| `POST` | `/api/chat/channels/{channel_id}/messages` | Enviar Mensagem |
| `GET` | `/api/chat/channels/{channel_id}/pinned` | Listar Pinadas |
| `POST` | `/api/chat/channels/{channel_id}/read` | Marcar Canal Lido |
| `GET` | `/api/chat/channels/{channel_id}/roles` | Listar Channel Roles |
| `PUT` | `/api/chat/channels/{channel_id}/roles` | Set Channel Roles |
| `GET` | `/api/chat/channels/{channel_id}/search` | Buscar Mensagens |
| `POST` | `/api/chat/channels/{channel_id}/silenciar` | Silenciar Canal |
| `DELETE` | `/api/chat/channels/{channel_id}/silenciar` | Desmutar Canal |
| `POST` | `/api/chat/channels/{channel_id}/upload` | Upload Imagem |
| `POST` | `/api/chat/channels/{channel_id}/voice/ata/start` | Voice Ata Start |
| `POST` | `/api/chat/channels/{channel_id}/voice/ata/stop` | Voice Ata Stop |
| `GET` | `/api/chat/channels/{channel_id}/voice/atas` | Voice Atas Do Canal |
| `POST` | `/api/chat/channels/{channel_id}/voice/join` | Voice Join |
| `POST` | `/api/chat/channels/{channel_id}/voice/leave` | Voice Leave |
| `GET` | `/api/chat/channels/{channel_id}/voice/peers` | Voice Peers |
| `GET` | `/api/chat/invites/{code}` | Info Invite |
| `POST` | `/api/chat/invites/{code}/accept` | Aceitar Invite |
| `DELETE` | `/api/chat/invites/{invite_id}` | Revogar Invite |
| `GET` | `/api/chat/me` | Me |
| `POST` | `/api/chat/me/avatar` | Upload Avatar User |
| `PATCH` | `/api/chat/messages/{message_id}` | Editar Mensagem |
| `DELETE` | `/api/chat/messages/{message_id}` | Deletar Mensagem |
| `POST` | `/api/chat/messages/{message_id}/pin` | Toggle Pin |
| `POST` | `/api/chat/messages/{message_id}/reactions` | Toggle Reacao |
| `GET` | `/api/chat/presence` | Get All Presence |
| `POST` | `/api/chat/presence` | Set Status Manual |
| `POST` | `/api/chat/push/subscribe` | Push Subscribe |
| `POST` | `/api/chat/push/unsubscribe` | Push Unsubscribe |
| `GET` | `/api/chat/push/vapid-public-key` | Vapid Public Key |
| `PATCH` | `/api/chat/roles/{role_id}` | Editar Role |
| `DELETE` | `/api/chat/roles/{role_id}` | Excluir Role |
| `GET` | `/api/chat/roles/{role_id}/members` | Listar Role Members |
| `POST` | `/api/chat/roles/{role_id}/members` | Add Role Members |
| `DELETE` | `/api/chat/roles/{role_id}/members/{user_id}` | Remove Role Member |
| `GET` | `/api/chat/servers` | Listar Servers |
| `POST` | `/api/chat/servers` | Criar Server |
| `GET` | `/api/chat/servers/{server_id}` | Detalhar Server |
| `PATCH` | `/api/chat/servers/{server_id}` | Editar Server |
| `DELETE` | `/api/chat/servers/{server_id}` | Arquivar Server |
| `POST` | `/api/chat/servers/{server_id}/avatar` | Upload Avatar Server |
| `POST` | `/api/chat/servers/{server_id}/categories` | Criar Categoria |
| `GET` | `/api/chat/servers/{server_id}/invites` | Listar Invites |
| `POST` | `/api/chat/servers/{server_id}/invites` | Criar Invite |
| `GET` | `/api/chat/servers/{server_id}/members` | Listar Membros Server Endpoint |
| `POST` | `/api/chat/servers/{server_id}/members` | Adicionar Membros Server |
| `PATCH` | `/api/chat/servers/{server_id}/members/{user_id}` | Editar Role Membro Server |
| `DELETE` | `/api/chat/servers/{server_id}/members/{user_id}` | Remover Membro Server |
| `GET` | `/api/chat/servers/{server_id}/roles` | Listar Roles |
| `POST` | `/api/chat/servers/{server_id}/roles` | Criar Role |
| `GET` | `/api/chat/users-disponiveis` | Listar Users Disponiveis |
| `GET` | `/api/chat/voice-atas/{ata_id}` | Voice Ata Get |

## Clicksign

| Método | Path | Descrição |
|---|---|---|
| `POST` | `/api/clicksign/termo-notebook` | Termo Notebook |

## comercial

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/comercial/clientes` | Listar Clientes |
| `POST` | `/api/comercial/clientes` | Criar Ou Reusar Cliente |
| `GET` | `/api/comercial/clientes/buscar` | Buscar Cliente Por Email |
| `GET` | `/api/comercial/clientes/{cliente_id}` | Detalhes Cliente |
| `GET` | `/api/comercial/clientes/{cliente_id}/reunioes` | Historico Reunioes Cliente |
| `GET` | `/api/comercial/material-apoio` | Listar Material |
| `POST` | `/api/comercial/material-apoio` | Upload Material |
| `PUT` | `/api/comercial/material-apoio/{material_id}` | Atualizar Material |
| `DELETE` | `/api/comercial/material-apoio/{material_id}` | Deletar Material |
| `GET` | `/api/comercial/reunioes` | Listar Reunioes |
| `POST` | `/api/comercial/reunioes` | Criar Reuniao |
| `GET` | `/api/comercial/reunioes/{reuniao_id}` | Detalhes Reuniao |
| `POST` | `/api/comercial/reunioes/{reuniao_id}/cancelar` | Cancelar Reuniao |
| `POST` | `/api/comercial/reunioes/{reuniao_id}/classificar` | Classificar Reuniao |
| `GET` | `/api/comercial/slots` | Slots Do User Atual |
| `GET` | `/api/comercial/slots/{vendedor_id}` | Slots De Vendedor |
| `PUT` | `/api/comercial/slots/{vendedor_id}` | Salvar Slots |
| `GET` | `/api/comercial/vendedores` | Listar Vendedores |

## Contratos

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/contratos` | List Contratos |
| `POST` | `/api/contratos` | Upload Contrato |
| `GET` | `/api/contratos/pastas` | List Pastas |
| `POST` | `/api/contratos/pastas` | Create Pasta |
| `DELETE` | `/api/contratos/pastas/{pasta_id}` | Delete Pasta |
| `POST` | `/api/contratos/pastas/{pasta_id}/copy` | Copy Pasta |
| `PUT` | `/api/contratos/pastas/{pasta_id}/move` | Move Pasta |
| `DELETE` | `/api/contratos/{contrato_id}` | Delete Contrato |
| `POST` | `/api/contratos/{contrato_id}/copy` | Copy Contrato |
| `PUT` | `/api/contratos/{contrato_id}/move` | Move Contrato |

## dashboard

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/dashboard/me` | Dashboard Me |

## email-preferencias

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/users/{user_id}/email-preferencias` | Obter Preferencias |
| `PUT` | `/api/users/{user_id}/email-preferencias` | Atualizar Preferencias |

## Fleet

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/fleet/checklists` | List Checklists |
| `POST` | `/api/fleet/checklists` | Create Checklist |
| `GET` | `/api/fleet/checklists/{checklist_id}` | Get Checklist |
| `POST` | `/api/fleet/checklists/{checklist_id}/aprovar` | Aprovar Checklist |
| `PUT` | `/api/fleet/checklists/{checklist_id}/devolver` | Devolver Veiculo |
| `POST` | `/api/fleet/checklists/{checklist_id}/iniciar-viagem` | Iniciar Viagem |
| `POST` | `/api/fleet/checklists/{checklist_id}/photos` | Upload Checklist Photo |
| `POST` | `/api/fleet/checklists/{checklist_id}/recusar-retorno` | Recusar Retorno |
| `POST` | `/api/fleet/checklists/{checklist_id}/scratch-data` | Save Scratch Data |
| `POST` | `/api/fleet/checklists/{checklist_id}/vistoriar-retorno` | Vistoriar Retorno |
| `POST` | `/api/fleet/checklists/{checklist_id}/vistoriar-saida` | Vistoriar Saida |
| `GET` | `/api/fleet/cost-centers` | Cost Centers |
| `GET` | `/api/fleet/dashboard` | Get Dashboard |
| `POST` | `/api/fleet/km-alerts` | Create Km Alert |
| `DELETE` | `/api/fleet/km-alerts/{alert_id}` | Delete Km Alert |
| `POST` | `/api/fleet/km-alerts/{alert_id}/dismiss` | Dismiss Km Alert |
| `GET` | `/api/fleet/km-alerts/{vehicle_id}` | List Km Alerts |
| `GET` | `/api/fleet/liberadores` | List Liberadores |
| `GET` | `/api/fleet/maintenance` | List Maintenance |
| `POST` | `/api/fleet/maintenance` | Create Maintenance |
| `DELETE` | `/api/fleet/maintenance-files/{file_id}` | Delete Maintenance File |
| `GET` | `/api/fleet/maintenance-types` | List Maintenance Types |
| `POST` | `/api/fleet/maintenance-types` | Create Maintenance Type |
| `DELETE` | `/api/fleet/maintenance-types/{type_id}` | Delete Maintenance Type |
| `PUT` | `/api/fleet/maintenance/{maintenance_id}` | Update Maintenance |
| `DELETE` | `/api/fleet/maintenance/{maintenance_id}` | Delete Maintenance |
| `GET` | `/api/fleet/maintenance/{maintenance_id}/files` | List Maintenance Files |
| `POST` | `/api/fleet/maintenance/{maintenance_id}/files` | Upload Maintenance File |
| `GET` | `/api/fleet/motoristas` | List Motoristas |
| `GET` | `/api/fleet/notifications` | Get Notifications |
| `GET` | `/api/fleet/reservations` | List Reservations |
| `POST` | `/api/fleet/reservations` | Create Reservation |
| `DELETE` | `/api/fleet/reservations/{res_id}` | Cancel Reservation |
| `POST` | `/api/fleet/reservations/{res_id}/approve` | Approve Reservation |
| `POST` | `/api/fleet/reservations/{res_id}/dismiss-notif` | Dismiss Reservation Notif |
| `POST` | `/api/fleet/reservations/{res_id}/reject` | Reject Reservation |
| `GET` | `/api/fleet/trips` | List Trips |
| `POST` | `/api/fleet/trips` | Create Trip |
| `PUT` | `/api/fleet/trips/{trip_id}` | Update Trip |
| `DELETE` | `/api/fleet/trips/{trip_id}` | Delete Trip |
| `GET` | `/api/fleet/unidades` | List Unidades |
| `GET` | `/api/fleet/vehicles` | List Vehicles |
| `POST` | `/api/fleet/vehicles` | Create Vehicle |
| `PUT` | `/api/fleet/vehicles/{vehicle_id}` | Update Vehicle |
| `DELETE` | `/api/fleet/vehicles/{vehicle_id}` | Delete Vehicle |
| `GET` | `/api/fleet/vehicles/{vehicle_id}/active-maintenance` | Vehicle Active Maintenance |
| `POST` | `/api/fleet/vehicles/{vehicle_id}/corrigir-avaria` | Corrigir Avaria |
| `POST` | `/api/fleet/vehicles/{vehicle_id}/forcar-vistoria` | Forcar Vistoria Admin |
| `GET` | `/api/fleet/vehicles/{vehicle_id}/history` | Get Vehicle History |
| `POST` | `/api/fleet/vehicles/{vehicle_id}/liberar` | Liberar Veiculo |
| `POST` | `/api/fleet/vehicles/{vehicle_id}/photo` | Upload Vehicle Photo |
| `DELETE` | `/api/fleet/vehicles/{vehicle_id}/photo/{photo_id}` | Delete Vehicle Photo |
| `GET` | `/api/fleet/vehicles/{vehicle_id}/photos` | Get Vehicle Photos |
| `POST` | `/api/fleet/vehicles/{vehicle_id}/reativar` | Reativar Veiculo |
| `POST` | `/api/fleet/vehicles/{vehicle_id}/status` | Change Vehicle Status |
| `POST` | `/api/fleet/vehicles/{vehicle_id}/subscribe` | Subscribe Vehicle Return |
| `DELETE` | `/api/fleet/vehicles/{vehicle_id}/subscribe` | Unsubscribe Vehicle Return |
| `GET` | `/api/fleet/vehicles/{vehicle_id}/subscription` | Get Vehicle Subscription |

## groups

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/groups/` | Get Groups |
| `POST` | `/api/groups/` | Create Group |
| `GET` | `/api/groups/departments` | List Departments |
| `POST` | `/api/groups/departments` | Create Department |
| `PUT` | `/api/groups/departments/{dept_id}` | Update Department |
| `DELETE` | `/api/groups/departments/{dept_id}` | Delete Department |
| `GET` | `/api/groups/{group_id}` | Get Group |
| `PUT` | `/api/groups/{group_id}` | Update Group |
| `DELETE` | `/api/groups/{group_id}` | Delete Group |

## interacoes

| Método | Path | Descrição |
|---|---|---|
| `POST` | `/api/ticket-interacoes/` | Criar Interacao |
| `GET` | `/api/ticket-interacoes/{ticket_id}` | Obter Interacoes |

## inventario

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/inventario/agent/download` | Agent Download |
| `POST` | `/api/inventario/agent/report` | Receber Relatorio |
| `GET` | `/api/inventario/agent/version` | Agent Version |
| `GET` | `/api/inventario/celulares` | Listar Celulares |
| `POST` | `/api/inventario/celulares` | Criar Celular |
| `GET` | `/api/inventario/celulares/{cel_id}` | Detalhe Celular |
| `PUT` | `/api/inventario/celulares/{cel_id}` | Atualizar Celular |
| `DELETE` | `/api/inventario/celulares/{cel_id}` | Deletar Celular |
| `GET` | `/api/inventario/celulares/{cel_id}/termo` | Dados Termo Celular |
| `GET` | `/api/inventario/dispositivos` | Listar Dispositivos |
| `GET` | `/api/inventario/dispositivos/{device_id}` | Detalhe Dispositivo |
| `DELETE` | `/api/inventario/dispositivos/{device_id}` | Remover Dispositivo |
| `PATCH` | `/api/inventario/dispositivos/{device_id}/apelido` | Atualizar Apelido |
| `PATCH` | `/api/inventario/dispositivos/{device_id}/estoque` | Atualizar Estoque |
| `PATCH` | `/api/inventario/dispositivos/{device_id}/info` | Atualizar Info |
| `GET` | `/api/inventario/fornecedores` | Fornecedores Listar |
| `POST` | `/api/inventario/fornecedores` | Fornecedores Criar |
| `PUT` | `/api/inventario/fornecedores/{forn_id}` | Fornecedores Atualizar |
| `DELETE` | `/api/inventario/fornecedores/{forn_id}` | Fornecedores Excluir |
| `GET` | `/api/inventario/itens` | Itens Listar |
| `POST` | `/api/inventario/itens` | Itens Criar |
| `GET` | `/api/inventario/itens/dispositivos-disponiveis` | Itens Dispositivos Disponiveis |
| `GET` | `/api/inventario/itens/stats` | Itens Stats |
| `PUT` | `/api/inventario/itens/{item_id}` | Itens Atualizar |
| `DELETE` | `/api/inventario/itens/{item_id}` | Itens Excluir |
| `PATCH` | `/api/inventario/itens/{item_id}/inativar` | Itens Inativar |
| `PATCH` | `/api/inventario/itens/{item_id}/reativar` | Itens Reativar |
| `GET` | `/api/inventario/manutencoes` | Manutencoes Listar |
| `POST` | `/api/inventario/manutencoes` | Manutencao Criar |
| `GET` | `/api/inventario/manutencoes/{manut_id}` | Manutencao Detalhe |
| `PUT` | `/api/inventario/manutencoes/{manut_id}` | Manutencao Atualizar |
| `DELETE` | `/api/inventario/manutencoes/{manut_id}` | Manutencao Excluir |
| `GET` | `/api/inventario/manutencoes/{manut_id}/orcamento` | Manutencao Baixar Orcamento |
| `GET` | `/api/inventario/omada/clients` | Omada Clients |
| `GET` | `/api/inventario/omada/devices` | Omada Devices |
| `GET` | `/api/inventario/omada/sites` | Omada Sites |
| `GET` | `/api/inventario/omada/topology` | Omada Topology |
| `GET` | `/api/inventario/stats` | Estatisticas |

## knowledge-base

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/kb/articles` | Listar Artigos |
| `POST` | `/api/kb/articles` | Criar Artigo |
| `GET` | `/api/kb/articles/{article_id}` | Detalhar Artigo |
| `PUT` | `/api/kb/articles/{article_id}` | Editar Artigo |
| `DELETE` | `/api/kb/articles/{article_id}` | Excluir Artigo |
| `POST` | `/api/kb/articles/{article_id}/helpful` | Marcar Helpful |
| `GET` | `/api/kb/groups` | Listar Grupos Disponiveis |
| `GET` | `/api/kb/stats` | Stats |
| `POST` | `/api/kb/upload-image` | Upload Imagem |

## meetings

| Método | Path | Descrição |
|---|---|---|
| `POST` | `/api/meetings/` | Criar Meeting |
| `GET` | `/api/meetings/atas/me` | Atas Minhas |
| `GET` | `/api/meetings/atas/{ata_id}` | Ata Get |
| `GET` | `/api/meetings/info/{code}` | Info Meeting |
| `GET` | `/api/meetings/turn-credentials` | Get Turn Credentials |
| `DELETE` | `/api/meetings/{code}` | Encerrar Meeting |
| `POST` | `/api/meetings/{code}/approve/{peer_id}` | Approve Guest |
| `POST` | `/api/meetings/{code}/ata/start` | Ata Start |
| `POST` | `/api/meetings/{code}/ata/stop` | Ata Stop |
| `POST` | `/api/meetings/{code}/leave/{peer_id}` | Leave Meeting |
| `GET` | `/api/meetings/{code}/participants` | Listar Participantes |
| `POST` | `/api/meetings/{code}/reject/{peer_id}` | Reject Guest |
| `POST` | `/api/meetings/{code}/request-entry` | Request Entry |

## network

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/network/events` | Eventos |
| `GET` | `/api/network/history` | Historico |
| `GET` | `/api/network/status` | Live Status |
| `GET` | `/api/network/units` | List Units |
| `POST` | `/api/network/units` | Create Unit |
| `PUT` | `/api/network/units/{unit_id}` | Update Unit |
| `DELETE` | `/api/network/units/{unit_id}` | Delete Unit |

## notificacoes

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/notificacoes/` | Listar notificaÃ§Ãµes |
| `DELETE` | `/api/notificacoes/limpador/lidas` | Limpar notificaÃ§Ãµes lidas |
| `GET` | `/api/notificacoes/nao-lidas/{usuario_id}` | Contar notificaÃ§Ãµes nÃ£o lidas |
| `GET` | `/api/notificacoes/usuario/{usuario_id}` | Listar notificaÃ§Ãµes do usuÃ¡rio |
| `PUT` | `/api/notificacoes/{notificacao_id}` | Atualizar notificaÃ§Ã£o |

## Passwords

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/passwords/` | List Passwords |
| `POST` | `/api/passwords/` | Create Password |
| `GET` | `/api/passwords/groups/list` | List Groups |
| `POST` | `/api/passwords/import` | Import Passwords |
| `POST` | `/api/passwords/vault-pin/reset` | Vault Pin Reset |
| `POST` | `/api/passwords/vault-pin/set` | Vault Pin Set |
| `GET` | `/api/passwords/vault-pin/status` | Vault Pin Status |
| `GET` | `/api/passwords/vault-pin/users-status` | Vault Pin Users Status |
| `POST` | `/api/passwords/vault-pin/verify` | Vault Pin Verify |
| `GET` | `/api/passwords/{password_id}` | Get Password |
| `PUT` | `/api/passwords/{password_id}` | Update Password |
| `DELETE` | `/api/passwords/{password_id}` | Delete Password |

## Permissions

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/permissions/catalog` | Get Catalog |
| `PUT` | `/api/permissions/catalog/{page_key}` | Update Catalog Page |
| `GET` | `/api/permissions/check` | Check Access |
| `GET` | `/api/permissions/exceptions` | Get Exceptions |
| `POST` | `/api/permissions/exceptions` | Create Exception |
| `GET` | `/api/permissions/exceptions/user/{user_id}` | Get User Exceptions |
| `DELETE` | `/api/permissions/exceptions/user/{user_id}` | Delete User Exceptions |
| `DELETE` | `/api/permissions/exceptions/{exception_id}` | Delete Exception |
| `GET` | `/api/permissions/me/menu` | Get My Menu |

## pre-cadastro

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/pre-cadastro/emails` | Listar Emails |
| `POST` | `/api/pre-cadastro/emails` | Adicionar Email Manual |
| `DELETE` | `/api/pre-cadastro/emails/{email_id}` | Remover Email |
| `GET` | `/api/pre-cadastro/grupos-publicos` | Listar Grupos Publicos |
| `GET` | `/api/pre-cadastro/pendentes` | Listar Pendentes |
| `POST` | `/api/pre-cadastro/solicitar` | Solicitar Cadastro |
| `GET` | `/api/pre-cadastro/unidades-publicas` | Listar Unidades Publicas |
| `POST` | `/api/pre-cadastro/upload-csv` | Upload Csv |
| `GET` | `/api/pre-cadastro/verificar-email` | Verificar Email |
| `GET` | `/api/pre-cadastro/verificar-username` | Verificar Username |
| `POST` | `/api/pre-cadastro/{pendente_id}/aprovar` | Aprovar |
| `POST` | `/api/pre-cadastro/{pendente_id}/recusar` | Recusar |

## recepcao

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/recepcao/convites/usuario/{usuario_id}` | List Convites Usuario |
| `POST` | `/api/recepcao/convites/{convite_id}/responder` | Responder Convite |
| `GET` | `/api/recepcao/envios` | List Envios |
| `POST` | `/api/recepcao/envios` | Create Envio |
| `PUT` | `/api/recepcao/envios/{envio_id}` | Update Envio |
| `DELETE` | `/api/recepcao/envios/{envio_id}` | Delete Envio |
| `GET` | `/api/recepcao/envios/{envio_id}/eventos` | Listar Eventos |
| `POST` | `/api/recepcao/envios/{envio_id}/eventos` | Criar Evento |
| `GET` | `/api/recepcao/envios/{envio_id}/rastrear` | Rastrear Via Api |
| `GET` | `/api/recepcao/escritorios` | List Escritorios |
| `POST` | `/api/recepcao/escritorios` | Create Escritorio |
| `PUT` | `/api/recepcao/escritorios/{escritorio_id}` | Update Escritorio |
| `DELETE` | `/api/recepcao/escritorios/{escritorio_id}` | Delete Escritorio |
| `PUT` | `/api/recepcao/eventos/{evento_id}` | Atualizar Evento |
| `DELETE` | `/api/recepcao/eventos/{evento_id}` | Deletar Evento |
| `GET` | `/api/recepcao/reservas` | List Reservas |
| `POST` | `/api/recepcao/reservas` | Create Reserva |
| `POST` | `/api/recepcao/reservas/{reserva_id}/cancelar` | Cancelar Reserva |
| `POST` | `/api/recepcao/reservas/{reserva_id}/confirmar` | Confirmar Reserva |
| `GET` | `/api/recepcao/reservas/{reserva_id}/convidados` | List Convidados |
| `POST` | `/api/recepcao/reservas/{reserva_id}/convidar` | Convidar Para Reserva |
| `GET` | `/api/recepcao/salas` | List Salas |
| `POST` | `/api/recepcao/salas` | Create Sala |
| `PUT` | `/api/recepcao/salas/{sala_id}` | Update Sala |
| `DELETE` | `/api/recepcao/salas/{sala_id}` | Delete Sala |

## security

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/security/banned` | Listar Banidos |
| `POST` | `/api/security/unban/{ip}` | Desbanir |

## subcategorias

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/subcategorias/` | Listar Subcategorias |
| `POST` | `/api/subcategorias/` | Criar Subcategoria |
| `PUT` | `/api/subcategorias/{subcategoria_id}` | Atualizar Subcategoria |
| `DELETE` | `/api/subcategorias/{subcategoria_id}` | Deletar Subcategoria |

## Tasks

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/tasks` | Listar Tarefas |
| `POST` | `/api/tasks` | Criar Tarefa |
| `GET` | `/api/tasks/categorias` | Listar Categorias |
| `POST` | `/api/tasks/categorias` | Criar Categoria Route |
| `DELETE` | `/api/tasks/categorias/{cat_id}` | Deletar Categoria Route |
| `GET` | `/api/tasks/convites` | Listar Convites |
| `DELETE` | `/api/tasks/convites/{convite_id}` | Cancelar Convite |
| `PUT` | `/api/tasks/convites/{convite_id}/aceitar` | Aceitar Convite |
| `PUT` | `/api/tasks/convites/{convite_id}/recusar` | Recusar Convite |
| `GET` | `/api/tasks/espacos` | Listar Espacos |
| `POST` | `/api/tasks/espacos` | Criar Espaco |
| `DELETE` | `/api/tasks/espacos/{espaco_id}` | Excluir Espaco |
| `GET` | `/api/tasks/espacos/{espaco_id}/convites-pendentes` | Listar Convites Espaco |
| `GET` | `/api/tasks/espacos/{espaco_id}/grupos` | Listar Grupos Espaco |
| `POST` | `/api/tasks/espacos/{espaco_id}/grupos` | Convidar Grupo Espaco |
| `DELETE` | `/api/tasks/espacos/{espaco_id}/grupos/{group_id}` | Remover Grupo Espaco |
| `PUT` | `/api/tasks/espacos/{espaco_id}/grupos/{group_id}/sla` | Atualizar Sla Grupo |
| `GET` | `/api/tasks/espacos/{espaco_id}/membros` | Listar Membros Espaco |
| `POST` | `/api/tasks/espacos/{espaco_id}/membros` | Adicionar Membro Espaco |
| `DELETE` | `/api/tasks/espacos/{espaco_id}/membros/{uid}` | Remover Membro Espaco |
| `GET` | `/api/tasks/espacos/{espaco_id}/relatorio-grupos` | Relatorio Grupos |
| `GET` | `/api/tasks/grupos/lista` | Listar Grupos |
| `GET` | `/api/tasks/grupos/{group_id}/membros` | Membros Grupo |
| `GET` | `/api/tasks/status` | Listar Status |
| `POST` | `/api/tasks/status` | Criar Status |
| `PUT` | `/api/tasks/status/{status_id}` | Atualizar Status |
| `DELETE` | `/api/tasks/status/{status_id}` | Deletar Status |
| `GET` | `/api/tasks/templates` | Listar Templates |
| `POST` | `/api/tasks/templates` | Salvar Template |
| `DELETE` | `/api/tasks/templates/{template_id}` | Deletar Template |
| `POST` | `/api/tasks/upload-imagem` | Upload Imagem |
| `GET` | `/api/tasks/{tarefa_id}` | Detalhe Tarefa |
| `PUT` | `/api/tasks/{tarefa_id}` | Atualizar Tarefa |
| `DELETE` | `/api/tasks/{tarefa_id}` | Deletar Tarefa |
| `POST` | `/api/tasks/{tarefa_id}/categorias/{cat_id}` | Associar Categoria |
| `DELETE` | `/api/tasks/{tarefa_id}/categorias/{cat_id}` | Remover Categoria Tarefa |
| `GET` | `/api/tasks/{tarefa_id}/comentarios` | Listar Comentarios |
| `POST` | `/api/tasks/{tarefa_id}/comentarios` | Adicionar Comentario |
| `POST` | `/api/tasks/{tarefa_id}/devolver` | Devolver Tarefa |
| `POST` | `/api/tasks/{tarefa_id}/encaminhar` | Encaminhar Tarefa |
| `POST` | `/api/tasks/{tarefa_id}/etapas` | Criar Etapa |
| `PUT` | `/api/tasks/{tarefa_id}/etapas/{etapa_id}` | Atualizar Etapa |
| `DELETE` | `/api/tasks/{tarefa_id}/etapas/{etapa_id}` | Deletar Etapa |
| `POST` | `/api/tasks/{tarefa_id}/etapas/{etapa_id}/concluir` | Concluir Etapa |
| `POST` | `/api/tasks/{tarefa_id}/finalizar` | Finalizar Tarefa |
| `GET` | `/api/tasks/{tarefa_id}/historico` | Listar Historico |
| `GET` | `/api/tasks/{tarefa_id}/historico-status` | Historico Status Tarefa |
| `GET` | `/api/tasks/{tarefa_id}/membros` | Listar Membros Tarefa |
| `POST` | `/api/tasks/{tarefa_id}/membros/{uid}` | Adicionar Membro Tarefa |
| `DELETE` | `/api/tasks/{tarefa_id}/membros/{uid}` | Remover Membro Tarefa |
| `POST` | `/api/tasks/{tarefa_id}/reabrir` | Reabrir Tarefa |
| `GET` | `/api/tasks/{tarefa_id}/subtarefas` | Listar Subtarefas |
| `POST` | `/api/tasks/{tarefa_id}/subtarefas` | Criar Subtarefa |
| `PUT` | `/api/tasks/{tarefa_id}/subtarefas/{sub_id}` | Atualizar Subtarefa |
| `DELETE` | `/api/tasks/{tarefa_id}/subtarefas/{sub_id}` | Deletar Subtarefa |
| `PUT` | `/api/tasks/{tarefa_id}/tempo` | Atualizar Tempo |
| `GET` | `/api/tasks/{tarefa_id}/tempo-usuarios` | Tempo Usuarios Tarefa |

## tickets

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/tickets/` | Obter Tickets — filtros: `data_inicio`, `data_fim`, `status_id`, `responsavel_id`, `grupo_id`, `prioridade_id`, `categoria_id`, `subcategoria_id`, `vista=meus\|para_mim`, `pular`, `limite` |
| `POST` | `/api/tickets/` | Criar Ticket |
| `GET` | `/api/tickets/attachments/{attach_id}` | Baixar Attachment |
| `DELETE` | `/api/tickets/attachments/{attach_id}` | Deletar Attachment |
| `GET` | `/api/tickets/dashboard/sla` | Dashboard Sla |
| `GET` | `/api/tickets/{ticket_id}` | Obter Ticket |
| `PUT` | `/api/tickets/{ticket_id}` | Atualizar Ticket |
| `DELETE` | `/api/tickets/{ticket_id}` | Deletar Ticket |
| `POST` | `/api/tickets/{ticket_id}/assumir` | Assumir Ticket |
| `GET` | `/api/tickets/{ticket_id}/attachments` | Listar Attachments |
| `POST` | `/api/tickets/{ticket_id}/attachments` | Upload Attachment |
| `POST` | `/api/tickets/{ticket_id}/devolver` | Devolver Ticket |
| `POST` | `/api/tickets/{ticket_id}/encaminhar` | Encaminhar Ticket |
| `POST` | `/api/tickets/{ticket_id}/finalizar` | Finalizar Ticket |
| `POST` | `/api/tickets/{ticket_id}/reabrir` | Reabrir Ticket |
| `GET` | `/api/tickets/{ticket_id}/sla` | Status Sla |
| `POST` | `/api/tickets/{ticket_id}/sla/pausar` | Pausar Sla Manual |
| `POST` | `/api/tickets/{ticket_id}/sla/retomar` | Retomar Sla Manual |

## tickets-permissoes (permissão por categoria por membro — migration 089)

| Método | Path | Descrição |
|---|---|---|
| `GET`    | `/api/tickets/permissoes/grupo/{group_id}/membros` | Lista membros USER do grupo + resumo (quantas restrições, `ve_tudo` bool). ADMIN/RESP do grupo. |
| `GET`    | `/api/tickets/permissoes/user/{user_id}`           | Detalhes das restrições do membro + árvore de categorias/subcategorias do grupo pra popular UI. |
| `PUT`    | `/api/tickets/permissoes/user/{user_id}`           | Substitui todas restrições. Body: `{categorias: [{categoria_id, subcategoria_id?}, ...]}`. |
| `DELETE` | `/api/tickets/permissoes/user/{user_id}`           | Zera todas as restrições do membro (volta a ver tudo do grupo). |

## unidades

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/unidades/` | List Unidades |
| `POST` | `/api/unidades/` | Create Unidade |
| `GET` | `/api/unidades/{unidade_id}` | Get Unidade |
| `PUT` | `/api/unidades/{unidade_id}` | Update Unidade |
| `DELETE` | `/api/unidades/{unidade_id}` | Delete Unidade |

## untagged

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/` | Root |
| `GET` | `/health` | Health |

## users

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/api/users/` | Get Users |
| `POST` | `/api/users/` | Create User |
| `GET` | `/api/users/{user_id}` | Get User |
| `PUT` | `/api/users/{user_id}` | Update User |
| `DELETE` | `/api/users/{user_id}` | Delete User |
| `POST` | `/api/users/{user_id}/senha` | Change Password |

---

## WebSockets

| Path | Descrição |
|---|---|
| `WS /api/meetings/ws?code=X&peer_id=Y&guest_token=Z` | Signaling WebRTC + eventos de sala (aprovar, encerrar, gravar) |
| `WS /api/chat/ws` | Mensagens de chat em tempo real (canais, DMs, presence) |

Tipos de mensagem WS documentados nos handlers `server/routes/meetings.py` e `server/routes/chat.py`.