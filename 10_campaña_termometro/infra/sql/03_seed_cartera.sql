USE [CL_CARTERA];
GO
DELETE FROM dbo.TBL_HISTORIAL_CARTERA;
INSERT INTO dbo.TBL_HISTORIAL_CARTERA
  (RUT_DV, SUB_SEGME, NOMBRE_CLIENTE, SEGME, ID_GENESM, NOM_SM, NOM_SUP, RUT_SM, Etiqueta, cod_dni, RUT_SIN_DV, FECHA_INICIO, FECHA_FIN)
VALUES
  ('11111111-1', 'SUB-PYM', 'Cliente Uno SPA', 'Pymes', 'SM001', 'Zona Norte', 'Ana Soto', '99999999-9', 'Cliente Regular', 'DNI001', '111111111', 20260101, 20261231),
  ('22222222-2', 'SUB-PYM', 'Cliente Dos Ltda', 'Pymes', 'SM002', 'Zona Norte', 'Ana Soto', '99999999-9', 'Cliente Regular', 'DNI002', '222222222', 20260101, 20261231),
  ('33333333-3', 'SUB-GRA', 'Cliente Tres SA', 'Grandes Empresas', 'SM003', 'Zona Sur', 'Luis Pinto', '99999999-9', 'Cliente Regular', 'DNI003', '333333333', 20260101, 20261231),
  ('44444444-4', 'SUB-PYM', 'Cliente Cuatro SPA', 'Pymes', 'SM004', 'Zona Sur', 'Luis Pinto', '99999999-9', 'Cliente Regular', 'DNI004', '444444444', 20260101, 20261231),
  ('55555555-5', 'SUB-GRA', 'Cliente Cinco Ltda', 'Grandes Empresas', 'SM005', 'Zona Norte', 'Ana Soto', '99999999-9', 'Cliente VIP', 'DNI005', '555555555', 20260101, 20261231),
  ('66666666-6', 'SUB-PYM', 'Cliente Seis SPA', 'Pymes', 'SM006', 'Zona Sur', 'Luis Pinto', '99999999-9', 'Cliente Regular', 'DNI006', '666666666', 20260101, 20261231),
  ('77777777-7', 'SUB-GRA', 'Cliente Siete SA', 'Grandes Empresas', 'SM007', 'Zona Norte', 'Ana Soto', '99999999-9', 'Cliente Regular', 'DNI007', '777777777', 20260101, 20261231),
  ('88888888-8', 'SUB-PYM', 'Cliente Ocho Ltda', 'Pymes', 'SM008', 'Zona Sur', 'Luis Pinto', '99999999-9', 'Cliente Regular', 'DNI008', '888888888', 20260101, 20261231);
GO
