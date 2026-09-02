-- Schema SIROS/ANAC + Supabase. Execute no SQL Editor do Supabase.
create table if not exists aeroportos (
  id bigint generated always as identity primary key,
  icao text not null unique,
  iata text,
  nome text not null,
  cidade text not null,
  estado text not null,
  lat float8,
  lon float8
);

create table if not exists voos (
  id bigint generated always as identity primary key,
  data_referencia date not null,
  icao_empresa text not null,
  nome_empresa text,
  numero_voo text not null,
  etapa text not null default '1',
  icao_origem text not null,
  icao_destino text not null,
  hr_partida_utc time,
  hr_chegada_utc time,
  partida_iso timestamptz,
  chegada_iso timestamptz,
  equipamento text,
  assentos integer,
  tipo_operacao text,
  tipo_servico text,
  criado_em timestamptz not null default now()
);

alter table voos drop constraint if exists voos_unique;
alter table voos add constraint voos_unique unique (data_referencia, icao_empresa, numero_voo, icao_origem, icao_destino, etapa);
create index if not exists idx_voos_data on voos (data_referencia desc);
create index if not exists idx_voos_destino on voos (icao_destino);
create index if not exists idx_voos_origem on voos (icao_origem);

create table if not exists execucoes (
  id bigint generated always as identity primary key,
  iniciado_em timestamptz not null default now(),
  concluido_em timestamptz,
  aeroportos_buscados text[],
  voos_processados integer default 0,
  lotes_enviados integer default 0,
  erros integer default 0,
  status text default 'em_andamento',
  observacao text
);
create index if not exists idx_exec_concluido on execucoes (concluido_em desc);

create or replace view voos_completo as
select v.*, ao.nome as nome_origem, ao.cidade as cidade_origem, ao.estado as estado_origem,
       ad.nome as nome_destino, ad.cidade as cidade_destino, ad.estado as estado_destino
from voos v
left join aeroportos ao on ao.icao = v.icao_origem
left join aeroportos ad on ad.icao = v.icao_destino;

alter table aeroportos enable row level security;
alter table voos enable row level security;
alter table execucoes enable row level security;

drop policy if exists "leitura publica aeroportos" on aeroportos;
create policy "leitura publica aeroportos" on aeroportos for select using (true);
drop policy if exists "leitura publica voos" on voos;
create policy "leitura publica voos" on voos for select using (true);
drop policy if exists "leitura publica execucoes" on execucoes;
create policy "leitura publica execucoes" on execucoes for select using (true);

grant select on table aeroportos, voos, execucoes, voos_completo to anon;
grant select on table aeroportos, voos, execucoes, voos_completo to authenticated;
grant all on table aeroportos, voos, execucoes to service_role;
grant usage, select on all sequences in schema public to service_role;

insert into aeroportos (icao, iata, nome, cidade, estado) values
('SBCA','CAC','Aeroporto Regional do Oeste','Cascavel','Parana'),
('SBCT','CWB','Afonso Pena Internacional','Curitiba','Parana'),
('SBLO','LDB','General Leite de Castro','Londrina','Parana'),
('SBMG','MGF','Silvio Name Junior Regional','Maringa','Parana'),
('SBFI','IGU','Cataratas Internacional','Foz do Iguacu','Parana'),
('SBFL','FLN','Hercilio Luz Internacional','Florianopolis','Santa Catarina'),
('SBJV','JOI','Lauro Carneiro de Loyola','Joinville','Santa Catarina'),
('SBNF','NVT','Min. Victor Konder Internacional','Navegantes','Santa Catarina'),
('SBPA','POA','Salgado Filho Internacional','Porto Alegre','Rio Grande do Sul'),
('SBCX','CXJ','Hugo Cantergiani Regional','Caxias do Sul','Rio Grande do Sul'),
('SBGR','GRU','Guarulhos Internacional','Guarulhos','Sao Paulo'),
('SBSP','CGH','Congonhas','Sao Paulo','Sao Paulo'),
('SBKP','VCP','Viracopos Internacional','Campinas','Sao Paulo'),
('SBRP','RAO','Leite Lopes','Ribeirao Preto','Sao Paulo'),
('SBGL','GIG','Galeao Internacional','Rio de Janeiro','Rio de Janeiro'),
('SBRJ','SDU','Santos Dumont','Rio de Janeiro','Rio de Janeiro'),
('SBCF','CNF','Tancredo Neves Internacional','Belo Horizonte','Minas Gerais'),
('SBUL','UDI','Ten. Cel. Aviador Cesar Bombonato','Uberlandia','Minas Gerais'),
('SBMK','MOC','Mario Ribeiro','Montes Claros','Minas Gerais'),
('SBVT','VIX','Eurico de Aguiar Salles','Vitoria','Espirito Santo'),
('SBBR','BSB','JK Internacional','Brasilia','Distrito Federal'),
('SBGO','GYN','Santa Genoveva','Goiania','Goias'),
('SBCY','CGB','Marechal Rondon Internacional','Cuiaba','Mato Grosso'),
('SBCG','CGR','Antonio Joao Internacional','Campo Grande','Mato Grosso do Sul'),
('SBSV','SSA','Deputado Luis Eduardo Magalhaes','Salvador','Bahia'),
('SBFZ','FOR','Pinto Martins Internacional','Fortaleza','Ceara'),
('SBRF','REC','Guararapes Internacional','Recife','Pernambuco'),
('SBSL','SLZ','Cunha Machado Internacional','Sao Luis','Maranhao'),
('SBTE','THE','Sen. Petronio Portella','Teresina','Piaui'),
('SBJP','JPA','Pres. Castro Pinto Internacional','Joao Pessoa','Paraiba'),
('SBMO','MCZ','Zumbi dos Palmares Internacional','Maceio','Alagoas'),
('SBSE','AJU','Santa Maria','Aracaju','Sergipe'),
('SBSG','NAT','Sao Goncalo do Amarante Internacional','Natal','Rio Grande do Norte'),
('SBEG','MAO','Eduardo Gomes Internacional','Manaus','Amazonas'),
('SBBE','BEL','Val-de-Cans Internacional','Belem','Para'),
('SBSN','STM','Maestro Wilson Fonseca','Santarem','Para'),
('SBMQ','MCP','Alberto Alcolumbre Internacional','Macapa','Amapa'),
('SBBV','BVB','Atlas Brasil Cantanhede Internacional','Boa Vista','Roraima'),
('SBPV','PVH','Gov. Jorge Teixeira de Oliveira','Porto Velho','Rondonia'),
('SBRB','RBR','Placido de Castro Internacional','Rio Branco','Acre'),
('SBPJ','PMW','Brig. Lysias Rodrigues','Palmas','Tocantins')
on conflict (icao) do update set iata=excluded.iata, nome=excluded.nome, cidade=excluded.cidade, estado=excluded.estado;

-- historico_vra pode ser adicionado quando o importador mensal for ativado.
