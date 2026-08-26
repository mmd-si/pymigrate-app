from typing import Any
from pydantic import BaseModel


class ExternalAuthInfo(BaseModel):
    idPersona: str | None
    tipoDocumento: str | None
    nroDocumento: str | None
    nombre: str | None
    apellido: str | None
    grupo: str | None
    sucursal: str | None
    nroEmpleado: str | None
    usuario: str | None
    email: str | None
    estado: str | None
    eliminado: str | None
    idPerfil: str | None
    nombrePerfil: str | None
    idSucursal: str | None
    siglas: str | None
    id: str | None
    ordenamiento: str | None
    razonSocial: str | None
    nombreComercial: str | None
    rfc: str | None
    direccion: str | None
    ciudad: str | None
    municipio: str | None
    telefono: str | None
    migrada: Any
    activa: str | None
    estadoSuc: str | None
    visible: str | None
    ElConix_Companie: Any
    ElConix_CentroCosto: Any
    grupoSuc: str | None
    doc_jefe_unidad: str | None

class ExternalAuthLogin(BaseModel):
    idLogin: str | None
    idFake: str | None
    idOriginal: str | None
    idGeneral: str | None
    tipoLogin: str | None
    usuario: str | None
    clave: str | None
    clave64: str | None
    cambioClave: str | None
    primeraVez: str | None
    verificado: str | None
    estado: str | None
    created_at: str | None
    updated_at: str | None
    idPerfil: str | None
    estadoper: str | None


class ExternalAuthData(BaseModel):
    ip: str | None
    info: ExternalAuthInfo
    login: ExternalAuthLogin

class ExternalAuth(BaseModel):
    continuar: int
    mensaje: str
    datos: ExternalAuthData | str

    def can_continue(self) -> bool:
        return self.continuar == 1
