# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
# GENERATED FILE - DO NOT EDIT MANUALLY.
# Regenerate with: python -m genro_builders.contrib.xsd.codegen --xsd <path> --class-name FatturaPAElements --output <path>
# Source targetNamespace: http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2
"""Element mixin for the Italian PA electronic invoice (FatturaPA v1.2.3). Generated from the official XSD published by Agenzia delle Entrate. Pair with BagBuilderBase via FatturaPABuilder in builder.py."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from genro_builders.builder import Range, Regex, element


class FatturaPAElements:
    """Element mixin generated from XSD namespace ``http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2``.

    Pair with ``BagBuilderBase`` in a concrete builder class.

    NOTE: the source XSD declares additional namespace imports that are not introspected by the current codegen:
        - http://www.w3.org/2000/09/xmldsig#
    """

    @element(
        sub_tags='FatturaElettronicaHeader[1],FatturaElettronicaBody[1:],Signature[0:1]',
    )
    def FatturaElettronica(self, versione: Literal['FPA12', 'FPR12'] | None = None, SistemaEmittente: Annotated[str, Regex('(\\p{IsBasicLatin}{1,10})')] | None = None):
        """XML schema fatture destinate a PA e privati in forma ordinaria 1.2.3 Args: versione, SistemaEmittente."""
        ...

    @element(
        sub_tags='DatiTrasmissione[1],CedentePrestatore[1],RappresentanteFiscale[0:1],CessionarioCommittente[1],TerzoIntermediarioOSoggettoEmittente[0:1],SoggettoEmittente[0:1]',
    )
    def FatturaElettronicaHeader(self):
        ...

    @element(
        sub_tags='IdTrasmittente[1],ProgressivoInvio[1],FormatoTrasmissione[1],CodiceDestinatario[1],ContattiTrasmittente[0:1],PECDestinatario[0:1]',
    )
    def DatiTrasmissione(self):
        ...

    @element(
        sub_tags='IdPaese[1],IdCodice[1]',
    )
    def IdTrasmittente(self):
        ...

    @element()
    def IdPaese(self, node_value: Annotated[str, Regex('[A-Z]{2}')] | None = None):
        """Args: node_value."""
        ...

    # NOTE: node_value: length [1..28] not emitted (grammar gap)
    @element()
    def IdCodice(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def ProgressivoInvio(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,10})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def FormatoTrasmissione(self, node_value: Literal['FPA12', 'FPR12'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CodiceDestinatario(self, node_value: Annotated[str, Regex('[A-Z0-9]{6,7}')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Telefono[0:1],Email[0:1]',
    )
    def ContattiTrasmittente(self):
        ...

    @element()
    def Telefono(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{5,12})')] | None = None):
        """Args: node_value."""
        ...

    # NOTE: node_value: length [7..256] not emitted (grammar gap)
    @element()
    def Email(self, node_value: Annotated[str, Regex('.+@.+[.]+.+')] | None = None):
        """Args: node_value."""
        ...

    # NOTE: node_value: length [0..256] not emitted (grammar gap)
    @element()
    def PECDestinatario(self, node_value: Annotated[str, Regex('([!#-\'*+/-9=?A-Z^-~-]+(\\.[!#-\'*+/-9=?A-Z^-~-]+)*|"(\\[\\]!#-[^-~ \\t]|(\\\\[\\t -~]))+")@([!#-\'*+/-9=?A-Z^-~-]+(\\.[!#-\'*+/-9=?A-Z^-~-]+)*|\\[[\\t -Z^-~]*\\])')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='DatiAnagrafici[1],Sede[1],StabileOrganizzazione[0:1],IscrizioneREA[0:1],Contatti[0:1],RiferimentoAmministrazione[0:1]',
    )
    def CedentePrestatore(self):
        ...

    @element(
        sub_tags='IdFiscaleIVA[1],CodiceFiscale[0:1],Anagrafica[1],AlboProfessionale[0:1],ProvinciaAlbo[0:1],NumeroIscrizioneAlbo[0:1],DataIscrizioneAlbo[0:1],RegimeFiscale[1]',
    )
    def DatiAnagrafici(self):
        ...

    @element(
        sub_tags='IdPaese[1],IdCodice[1]',
    )
    def IdFiscaleIVA(self):
        ...

    @element()
    def CodiceFiscale(self, node_value: Annotated[str, Regex('[A-Z0-9]{11,16}')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Denominazione[1],Nome[1],Cognome[1],Titolo[0:1],CodEORI[0:1]',
    )
    def Anagrafica(self):
        ...

    @element()
    def Denominazione(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,80}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Nome(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,60}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Cognome(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,60}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Titolo(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{2,10})')] | None = None):
        """Args: node_value."""
        ...

    # NOTE: node_value: length [13..17] not emitted (grammar gap)
    @element()
    def CodEORI(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def AlboProfessionale(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,60}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ProvinciaAlbo(self, node_value: Annotated[str, Regex('[A-Z]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def NumeroIscrizioneAlbo(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,60})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataIscrizioneAlbo(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def RegimeFiscale(self, node_value: Literal['RF01', 'RF02', 'RF04', 'RF05', 'RF06', 'RF07', 'RF08', 'RF09', 'RF10', 'RF11', 'RF12', 'RF13', 'RF14', 'RF15', 'RF16', 'RF17', 'RF18', 'RF19', 'RF20'] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Indirizzo[1],NumeroCivico[0:1],CAP[1],Comune[1],Provincia[0:1],Nazione[1]',
    )
    def Sede(self):
        ...

    @element()
    def Indirizzo(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,60}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def NumeroCivico(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,8})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CAP(self, node_value: Annotated[str, Regex('[0-9][0-9][0-9][0-9][0-9]')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Comune(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,60}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Provincia(self, node_value: Annotated[str, Regex('[A-Z]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Nazione(self, node_value: Annotated[str, Regex('[A-Z]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Indirizzo[1],NumeroCivico[0:1],CAP[1],Comune[1],Provincia[0:1],Nazione[1]',
    )
    def StabileOrganizzazione(self):
        ...

    @element(
        sub_tags='Ufficio[1],NumeroREA[1],CapitaleSociale[0:1],SocioUnico[0:1],StatoLiquidazione[1]',
    )
    def IscrizioneREA(self):
        ...

    @element()
    def Ufficio(self, node_value: Annotated[str, Regex('[A-Z]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def NumeroREA(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,20})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CapitaleSociale(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def SocioUnico(self, node_value: Literal['SU', 'SM'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def StatoLiquidazione(self, node_value: Literal['LS', 'LN'] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Telefono[0:1],Fax[0:1],Email[0:1]',
    )
    def Contatti(self):
        ...

    @element()
    def Fax(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{5,12})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def RiferimentoAmministrazione(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,20})')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='DatiAnagrafici[1]',
    )
    def RappresentanteFiscale(self):
        ...

    @element(
        sub_tags='DatiAnagrafici[1],Sede[1],StabileOrganizzazione[0:1],RappresentanteFiscale[0:1]',
    )
    def CessionarioCommittente(self):
        ...

    @element(
        sub_tags='DatiAnagrafici[1]',
    )
    def TerzoIntermediarioOSoggettoEmittente(self):
        ...

    @element()
    def SoggettoEmittente(self, node_value: Literal['CC', 'TZ'] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='DatiGenerali[1],DatiBeniServizi[1],DatiVeicoli[0:1],DatiPagamento,Allegati',
    )
    def FatturaElettronicaBody(self):
        ...

    @element(
        sub_tags='DatiGeneraliDocumento[1],DatiOrdineAcquisto,DatiContratto,DatiConvenzione,DatiRicezione,DatiFattureCollegate,DatiSAL,DatiDDT,DatiTrasporto[0:1],FatturaPrincipale[0:1]',
    )
    def DatiGenerali(self):
        ...

    @element(
        sub_tags='TipoDocumento[1],Divisa[1],Data[1],Numero[1],DatiRitenuta,DatiBollo[0:1],DatiCassaPrevidenziale,ScontoMaggiorazione,ImportoTotaleDocumento[0:1],Arrotondamento[0:1],Causale,Art73[0:1]',
    )
    def DatiGeneraliDocumento(self):
        ...

    @element()
    def TipoDocumento(self, node_value: Literal['TD01', 'TD02', 'TD03', 'TD04', 'TD05', 'TD06', 'TD16', 'TD17', 'TD18', 'TD19', 'TD20', 'TD21', 'TD22', 'TD23', 'TD24', 'TD25', 'TD26', 'TD27', 'TD28', 'TD29'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Divisa(self, node_value: Annotated[str, Regex('[A-Z]{3}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Data(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def Numero(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,20})')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='TipoRitenuta[1],ImportoRitenuta[1],AliquotaRitenuta[1],CausalePagamento[1]',
    )
    def DatiRitenuta(self):
        ...

    @element()
    def TipoRitenuta(self, node_value: Literal['RT01', 'RT02', 'RT03', 'RT04', 'RT05', 'RT06'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ImportoRitenuta(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def AliquotaRitenuta(self, node_value: Annotated[Decimal, Regex('[0-9]{1,3}\\.[0-9]{2}'), Range(le=100.0)] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CausalePagamento(self, node_value: Literal['A', 'B', 'C', 'D', 'E', 'G', 'H', 'I', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'L1', 'M1', 'M2', 'O1', 'V1', 'ZO'] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='BolloVirtuale[1],ImportoBollo[0:1]',
    )
    def DatiBollo(self):
        ...

    @element()
    def BolloVirtuale(self, node_value: Literal['SI'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ImportoBollo(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='TipoCassa[1],AlCassa[1],ImportoContributoCassa[1],ImponibileCassa[0:1],AliquotaIVA[1],Ritenuta[0:1],Natura[0:1],RiferimentoAmministrazione[0:1]',
    )
    def DatiCassaPrevidenziale(self):
        ...

    @element()
    def TipoCassa(self, node_value: Literal['TC01', 'TC02', 'TC03', 'TC04', 'TC05', 'TC06', 'TC07', 'TC08', 'TC09', 'TC10', 'TC11', 'TC12', 'TC13', 'TC14', 'TC15', 'TC16', 'TC17', 'TC18', 'TC19', 'TC20', 'TC21', 'TC22'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def AlCassa(self, node_value: Annotated[Decimal, Regex('[0-9]{1,3}\\.[0-9]{2}'), Range(le=100.0)] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ImportoContributoCassa(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ImponibileCassa(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def AliquotaIVA(self, node_value: Annotated[Decimal, Regex('[0-9]{1,3}\\.[0-9]{2}'), Range(le=100.0)] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Ritenuta(self, node_value: Literal['SI'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Natura(self, node_value: Literal['N1', 'N2', 'N2.1', 'N2.2', 'N3', 'N3.1', 'N3.2', 'N3.3', 'N3.4', 'N3.5', 'N3.6', 'N4', 'N5', 'N6', 'N6.1', 'N6.2', 'N6.3', 'N6.4', 'N6.5', 'N6.6', 'N6.7', 'N6.8', 'N6.9', 'N7'] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Tipo[1],Percentuale[0:1],Importo[0:1]',
    )
    def ScontoMaggiorazione(self):
        ...

    @element()
    def Tipo(self, node_value: Literal['SC', 'MG'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Percentuale(self, node_value: Annotated[Decimal, Regex('[0-9]{1,3}\\.[0-9]{2}'), Range(le=100.0)] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Importo(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2,8}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ImportoTotaleDocumento(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Arrotondamento(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Causale(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,200}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Art73(self, node_value: Literal['SI'] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='RiferimentoNumeroLinea,IdDocumento[1],Data[0:1],NumItem[0:1],CodiceCommessaConvenzione[0:1],CodiceCUP[0:1],CodiceCIG[0:1]',
    )
    def DatiOrdineAcquisto(self):
        ...

    @element()
    def RiferimentoNumeroLinea(self, node_value: Annotated[Decimal, Range(ge=1.0, le=9999.0)] | None = None):
        """Args: node_value."""
        ...

    @element()
    def IdDocumento(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,20})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def NumItem(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,20})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CodiceCommessaConvenzione(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,100}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CodiceCUP(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,15})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CodiceCIG(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,15})')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='RiferimentoNumeroLinea,IdDocumento[1],Data[0:1],NumItem[0:1],CodiceCommessaConvenzione[0:1],CodiceCUP[0:1],CodiceCIG[0:1]',
    )
    def DatiContratto(self):
        ...

    @element(
        sub_tags='RiferimentoNumeroLinea,IdDocumento[1],Data[0:1],NumItem[0:1],CodiceCommessaConvenzione[0:1],CodiceCUP[0:1],CodiceCIG[0:1]',
    )
    def DatiConvenzione(self):
        ...

    @element(
        sub_tags='RiferimentoNumeroLinea,IdDocumento[1],Data[0:1],NumItem[0:1],CodiceCommessaConvenzione[0:1],CodiceCUP[0:1],CodiceCIG[0:1]',
    )
    def DatiRicezione(self):
        ...

    @element(
        sub_tags='RiferimentoNumeroLinea,IdDocumento[1],Data[0:1],NumItem[0:1],CodiceCommessaConvenzione[0:1],CodiceCUP[0:1],CodiceCIG[0:1]',
    )
    def DatiFattureCollegate(self):
        ...

    @element(
        sub_tags='RiferimentoFase[1]',
    )
    def DatiSAL(self):
        ...

    @element()
    def RiferimentoFase(self, node_value: Annotated[Decimal, Range(ge=1.0, le=999.0)] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='NumeroDDT[1],DataDDT[1],RiferimentoNumeroLinea',
    )
    def DatiDDT(self):
        ...

    @element()
    def NumeroDDT(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,20})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataDDT(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='DatiAnagraficiVettore[0:1],MezzoTrasporto[0:1],CausaleTrasporto[0:1],NumeroColli[0:1],Descrizione[0:1],UnitaMisuraPeso[0:1],PesoLordo[0:1],PesoNetto[0:1],DataOraRitiro[0:1],DataInizioTrasporto[0:1],TipoResa[0:1],IndirizzoResa[0:1],DataOraConsegna[0:1]',
    )
    def DatiTrasporto(self):
        ...

    @element(
        sub_tags='IdFiscaleIVA[1],CodiceFiscale[0:1],Anagrafica[1],NumeroLicenzaGuida[0:1]',
    )
    def DatiAnagraficiVettore(self):
        ...

    @element()
    def NumeroLicenzaGuida(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,20})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def MezzoTrasporto(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,80}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CausaleTrasporto(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,100}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def NumeroColli(self, node_value: Annotated[Decimal, Range(ge=1.0, le=9999.0)] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Descrizione(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,100}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def UnitaMisuraPeso(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,10})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def PesoLordo(self, node_value: Annotated[Decimal, Regex('[0-9]{1,4}\\.[0-9]{1,2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def PesoNetto(self, node_value: Annotated[Decimal, Regex('[0-9]{1,4}\\.[0-9]{1,2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataOraRitiro(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataInizioTrasporto(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def TipoResa(self, node_value: Annotated[str, Regex('[A-Z]{3}')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Indirizzo[1],NumeroCivico[0:1],CAP[1],Comune[1],Provincia[0:1],Nazione[1]',
    )
    def IndirizzoResa(self):
        ...

    @element()
    def DataOraConsegna(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='NumeroFatturaPrincipale[1],DataFatturaPrincipale[1]',
    )
    def FatturaPrincipale(self):
        ...

    @element()
    def NumeroFatturaPrincipale(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,20})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataFatturaPrincipale(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='DettaglioLinee[1:],DatiRiepilogo[1:]',
    )
    def DatiBeniServizi(self):
        ...

    @element(
        sub_tags='NumeroLinea[1],TipoCessionePrestazione[0:1],CodiceArticolo,Descrizione[1],Quantita[0:1],UnitaMisura[0:1],DataInizioPeriodo[0:1],DataFinePeriodo[0:1],PrezzoUnitario[1],ScontoMaggiorazione,PrezzoTotale[1],AliquotaIVA[1],Ritenuta[0:1],Natura[0:1],RiferimentoAmministrazione[0:1],AltriDatiGestionali',
    )
    def DettaglioLinee(self):
        ...

    @element()
    def NumeroLinea(self, node_value: Annotated[Decimal, Range(ge=1.0, le=9999.0)] | None = None):
        """Args: node_value."""
        ...

    @element()
    def TipoCessionePrestazione(self, node_value: Literal['SC', 'PR', 'AB', 'AC'] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='CodiceTipo[1],CodiceValore[1]',
    )
    def CodiceArticolo(self):
        ...

    @element()
    def CodiceTipo(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,35})')] | None = None):
        """Args: node_value."""
        ...

    # NOTE: node_value: length [1..35] not emitted (grammar gap)
    @element()
    def CodiceValore(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def Quantita(self, node_value: Annotated[Decimal, Regex('[0-9]{1,12}\\.[0-9]{2,8}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def UnitaMisura(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,10})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataInizioPeriodo(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataFinePeriodo(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def PrezzoUnitario(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2,8}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def PrezzoTotale(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2,8}')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='TipoDato[1],RiferimentoTesto[0:1],RiferimentoNumero[0:1],RiferimentoData[0:1]',
    )
    def AltriDatiGestionali(self):
        ...

    @element()
    def TipoDato(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,10})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def RiferimentoTesto(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,60}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def RiferimentoNumero(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2,8}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def RiferimentoData(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='AliquotaIVA[1],Natura[0:1],SpeseAccessorie[0:1],Arrotondamento[0:1],ImponibileImporto[1],Imposta[1],EsigibilitaIVA[0:1],RiferimentoNormativo[0:1]',
    )
    def DatiRiepilogo(self):
        ...

    @element()
    def SpeseAccessorie(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ImponibileImporto(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Imposta(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def EsigibilitaIVA(self, node_value: Literal['D', 'I', 'S'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def RiferimentoNormativo(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,100}')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Data[1],TotalePercorso[1]',
    )
    def DatiVeicoli(self):
        ...

    @element()
    def TotalePercorso(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,15})')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='CondizioniPagamento[1],DettaglioPagamento[1:]',
    )
    def DatiPagamento(self):
        ...

    @element()
    def CondizioniPagamento(self, node_value: Literal['TP01', 'TP02', 'TP03'] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Beneficiario[0:1],ModalitaPagamento[1],DataRiferimentoTerminiPagamento[0:1],GiorniTerminiPagamento[0:1],DataScadenzaPagamento[0:1],ImportoPagamento[1],CodUfficioPostale[0:1],CognomeQuietanzante[0:1],NomeQuietanzante[0:1],CFQuietanzante[0:1],TitoloQuietanzante[0:1],IstitutoFinanziario[0:1],IBAN[0:1],ABI[0:1],CAB[0:1],BIC[0:1],ScontoPagamentoAnticipato[0:1],DataLimitePagamentoAnticipato[0:1],PenalitaPagamentiRitardati[0:1],DataDecorrenzaPenale[0:1],CodicePagamento[0:1]',
    )
    def DettaglioPagamento(self):
        ...

    @element()
    def Beneficiario(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,200}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ModalitaPagamento(self, node_value: Literal['MP01', 'MP02', 'MP03', 'MP04', 'MP05', 'MP06', 'MP07', 'MP08', 'MP09', 'MP10', 'MP11', 'MP12', 'MP13', 'MP14', 'MP15', 'MP16', 'MP17', 'MP18', 'MP19', 'MP20', 'MP21', 'MP22', 'MP23'] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataRiferimentoTerminiPagamento(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def GiorniTerminiPagamento(self, node_value: Annotated[Decimal, Range(ge=0.0, le=999.0)] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataScadenzaPagamento(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def ImportoPagamento(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CodUfficioPostale(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,20})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CognomeQuietanzante(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,60}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def NomeQuietanzante(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,60}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CFQuietanzante(self, node_value: Annotated[str, Regex('[A-Z0-9]{16}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def TitoloQuietanzante(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{2,10})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def IstitutoFinanziario(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,80}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def IBAN(self, node_value: Annotated[str, Regex('[a-zA-Z]{2}[0-9]{2}[a-zA-Z0-9]{11,30}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ABI(self, node_value: Annotated[str, Regex('[0-9][0-9][0-9][0-9][0-9]')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def CAB(self, node_value: Annotated[str, Regex('[0-9][0-9][0-9][0-9][0-9]')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def BIC(self, node_value: Annotated[str, Regex('[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3}){0,1}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def ScontoPagamentoAnticipato(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataLimitePagamentoAnticipato(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def PenalitaPagamentiRitardati(self, node_value: Annotated[Decimal, Regex('[\\-]?[0-9]{1,11}\\.[0-9]{2}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DataDecorrenzaPenale(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def CodicePagamento(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,60})')] | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='NomeAttachment[1],AlgoritmoCompressione[0:1],FormatoAttachment[0:1],DescrizioneAttachment[0:1],Attachment[1]',
    )
    def Allegati(self):
        ...

    @element()
    def NomeAttachment(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,60}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def AlgoritmoCompressione(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,10})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def FormatoAttachment(self, node_value: Annotated[str, Regex('(\\p{IsBasicLatin}{1,10})')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def DescrizioneAttachment(self, node_value: Annotated[str, Regex('[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]{1,100}')] | None = None):
        """Args: node_value."""
        ...

    @element()
    def Attachment(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='SignedInfo[1],SignatureValue[1],KeyInfo[0:1],Object',
    )
    def Signature(self, Id: str | None = None):
        """Args: Id."""
        ...

    @element(
        sub_tags='CanonicalizationMethod[1],SignatureMethod[1],Reference[1:]',
    )
    def SignedInfo(self, Id: str | None = None):
        """Args: Id."""
        ...

    @element()
    def CanonicalizationMethod(self, Algorithm: str | None = None):
        """Args: Algorithm."""
        ...

    @element(
        sub_tags='HMACOutputLength[0:1]',
    )
    def SignatureMethod(self, Algorithm: str | None = None):
        """Args: Algorithm."""
        ...

    @element()
    def HMACOutputLength(self, node_value: Decimal | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Transforms[0:1],DigestMethod[1],DigestValue[1]',
    )
    def Reference(self, Id: str | None = None, URI: str | None = None, Type: str | None = None):
        """Args: Id, URI, Type."""
        ...

    @element(
        sub_tags='Transform[1:]',
    )
    def Transforms(self):
        ...

    @element(
        sub_tags='XPath[1]',
    )
    def Transform(self, Algorithm: str | None = None):
        """Args: Algorithm."""
        ...

    @element()
    def XPath(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def DigestMethod(self, Algorithm: str | None = None):
        """Args: Algorithm."""
        ...

    @element()
    def DigestValue(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def SignatureValue(self, node_value: str | None = None, Id: str | None = None):
        """Args: node_value, Id."""
        ...

    @element(
        sub_tags='KeyName[1],KeyValue[1],RetrievalMethod[1],X509Data[1],PGPData[1],SPKIData[1],MgmtData[1]',
    )
    def KeyInfo(self, Id: str | None = None):
        """Args: Id."""
        ...

    @element()
    def KeyName(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='DSAKeyValue[1],RSAKeyValue[1]',
    )
    def KeyValue(self):
        ...

    @element(
        sub_tags='P[1],Q[1],G[0:1],Y[1],J[0:1],Seed[1],PgenCounter[1]',
    )
    def DSAKeyValue(self):
        ...

    @element()
    def P(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def Q(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def G(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def Y(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def J(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def Seed(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def PgenCounter(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Modulus[1],Exponent[1]',
    )
    def RSAKeyValue(self):
        ...

    @element()
    def Modulus(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def Exponent(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='Transforms[0:1]',
    )
    def RetrievalMethod(self, URI: str | None = None, Type: str | None = None):
        """Args: URI, Type."""
        ...

    @element(
        sub_tags='X509IssuerSerial[1],X509SKI[1],X509SubjectName[1],X509Certificate[1],X509CRL[1]',
    )
    def X509Data(self):
        ...

    @element(
        sub_tags='X509IssuerName[1],X509SerialNumber[1]',
    )
    def X509IssuerSerial(self):
        ...

    @element()
    def X509IssuerName(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def X509SerialNumber(self, node_value: Decimal | None = None):
        """Args: node_value."""
        ...

    @element()
    def X509SKI(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def X509SubjectName(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def X509Certificate(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def X509CRL(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='PGPKeyID[1],PGPKeyPacket[0:1]',
    )
    def PGPData(self):
        ...

    @element()
    def PGPKeyID(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def PGPKeyPacket(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element(
        sub_tags='SPKISexp[1]',
    )
    def SPKIData(self):
        ...

    @element()
    def SPKISexp(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def MgmtData(self, node_value: str | None = None):
        """Args: node_value."""
        ...

    @element()
    def Object(self, Id: str | None = None, MimeType: str | None = None, Encoding: str | None = None):
        """Args: Id, MimeType, Encoding."""
        ...

