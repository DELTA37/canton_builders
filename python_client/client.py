import asyncio
import datetime
import decimal
import os
import sys
import traceback
from typing import Any, Dict, List, Optional

from dazl.ledger import ExerciseResponse
from dazl.ledger.api_types import ContractId
from dazl.damlast.daml_lf_1 import DottedName, ModuleRef, PackageRef, TypeConName
from dazl.damlast.daml_lf_1 import DottedName, ModuleRef, PackageRef, TypeConName
from dazl.damlast.daml_lf_1 import TypeConName
import dazl
from dazl import Party
from dazl.ledger.api_types import CreateEvent, ArchiveEvent


DEFAULT_LEDGER_HOST = os.getenv("LEDGER_HOST", "localhost")
DEFAULT_LEDGER_PORT = int(os.getenv("LEDGER_PORT", "26865"))
DEFAULT_PARTY = os.getenv("LEDGER_PARTY", "")
DEFAULT_APP_NAME = os.getenv("LEDGER_APP_NAME", "real-estate-client")


def to_jsonable(val: Any) -> Any:
    """
    Рекурсивно преобразует значения в JSON-совместимые типы.

    Обрабатывает специальные типы Daml/dazl (Decimal, datetime, CreateEvent)
    и рекурсивно преобразует вложенные структуры данных.

    Args:
        val: Значение для преобразования (любой тип).

    Returns:
        JSON-совместимое представление значения:
        - примитивы (str, int, float, bool, None) возвращаются как есть
        - Decimal -> str
        - datetime -> ISO формат строки
        - dict -> рекурсивно преобразованный dict
        - list/tuple/set -> рекурсивно преобразованный list
        - CreateEvent -> {"contractId": str, "payload": dict}
        - остальные типы -> str(val)
    """
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val
    if isinstance(val, decimal.Decimal):
        return str(val)
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: to_jsonable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [to_jsonable(v) for v in val]
    if isinstance(val, ContractId):
        return {
            "contractId": val.value,
            "contractType": str(val.value_type),
        }
    if isinstance(val, ExerciseResponse):
        return {
            "result": to_jsonable(val.result),
            "events": to_jsonable(val.events)
        }
    if isinstance(val, ArchiveEvent):
        return {
            "contractId": to_jsonable(val.contract_id),
        }
    if isinstance(val, CreateEvent):
        return {
            "contractId": to_jsonable(val.contract_id),
            "payload": to_jsonable(val.payload),
        }
    return str(val)


class RealEstateHandler:
    """
    Асинхронный клиент для взаимодействия с Daml леджером для контрактов RealEstate и Cash.

    Использует библиотеку dazl для подключения к Canton леджеру через gRPC API.
    Реализует паттерн async context manager для управления жизненным циклом соединения.

    Пример использования:
        async with RealEstateHandler(party="Registrar") as handler:
            result = await handler.create_property_async(...)

    Attributes:
        host: Хост леджера (по умолчанию localhost).
        port: Порт gRPC API леджера (по умолчанию 26865).
        party_hint: Подсказка для идентификации party (резолвится в канонический ID).
        app_name: Имя приложения для идентификации в леджере.
        client: Активное соединение dazl (устанавливается в __aenter__).
        party: Канонический ID party после резолюции.
    """

    def __init__(
        self,
        host: str = DEFAULT_LEDGER_HOST,
        port: int = DEFAULT_LEDGER_PORT,
        party: str = DEFAULT_PARTY,
        app_name: str = DEFAULT_APP_NAME,
    ):
        """
        Инициализирует handler для работы с леджером.

        Args:
            host: Хост леджера (например, "localhost").
            port: Порт gRPC API леджера.
            party: Подсказка для party (например, "Registrar", "Owner").
                   Будет резолвиться в канонический ID при подключении.
            app_name: Имя приложения для логирования в леджере.
        """
        self.host = host
        self.port = port
        self.party_hint = party or "Observer"
        self.app_name = app_name

        self.client = None
        self.party = None  # resolved party id
        self._template_type = None  # cached TypeConName for RealEstate template

    def _url(self) -> str:
        """
        Формирует gRPC URL для подключения к леджеру.

        Returns:
            URL строка формата "grpc://host:port".
        """
        return f"grpc://{self.host}:{self.port}"

    # =============================
    # CONTEXT MANAGER
    # =============================

    async def __aenter__(self):
        """
        Устанавливает соединение с леджером при входе в async context manager.

        Выполняет двухэтапное подключение:
        1. Временное соединение для резолюции party hint в канонический ID.
        2. Постоянное соединение с резолвнутым party для выполнения операций.

        Returns:
            self: Экземпляр RealEstateHandler с установленным соединением.

        Raises:
            Exception: При ошибках подключения к леджеру.
        """
        # First: connect with hint
        raw_conn = dazl.connect(
            url=self._url(),
            party=Party(self.party_hint),
            application_name=self.app_name,
        )
        resolver = await raw_conn.__aenter__()

        # Resolve actual party
        self.party = await self._resolve_party(resolver, self.party_hint)

        # resolver is no longer needed
        await raw_conn.__aexit__(None, None, None)

        # Second: open real session with resolved party
        conn = dazl.connect(
            url=self._url(),
            party=Party(self.party),
            read_as=[Party(self.party)],
            act_as=[Party(self.party)],
            application_name=self.app_name,
        )
        self.client = await conn.__aenter__()
        self._conn_cm = conn  # to close on exit
        await self.list_properties_async()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Закрывает соединение с леджером при выходе из async context manager.

        Args:
            exc_type: Тип исключения (если было).
            exc: Экземпляр исключения (если было).
            tb: Traceback исключения (если было).
        """
        if self.client is not None:
            await self._conn_cm.__aexit__(exc_type, exc, tb)
        self.client = None

    # =============================
    # HELPERS
    # =============================

    async def _resolve_party(self, conn, hint: str) -> str:
        """
        Резолвит подсказку party в канонический ID party.

        Ищет party по подсказке среди известных parties в леджере.
        Если подсказка уже содержит "::" (канонический формат), возвращает как есть.

        Args:
            conn: Активное dazl соединение для запроса parties.
            hint: Подсказка party (например, "Registrar", "Owner").

        Returns:
            Канонический ID party (например, "Registrar-123::abc...") или
            исходная подсказка, если party не найден.
        """
        if "::" in hint:
            return hint
        try:
            infos = await conn.list_known_parties()
            for info in infos:
                if str(info.party).startswith(f"{hint}-") or info.display_name == hint:
                    return str(info.party)
        except Exception:
            pass
        return hint

    async def _exercise(self, contract_id: str,
                        choice: str,
                        argument: Dict[str, Any], extra_act_as=None):
        """
        Выполняет choice на контракте RealEstate.

        Args:
            contract_id: ID контракта для выполнения choice.
            choice: Имя choice (например, "Transfer", "ListForSale").
            argument: Аргументы choice в виде словаря.
            extra_act_as: Дополнительные parties для multi-controller choices
                          (например, для Buy нужны buyer и seller).

        Returns:
            JSON-совместимый результат выполнения choice.

        Raises:
            Exception: При ошибках выполнения choice (валидация, авторизация и т.д.).
        """
        act_as = [Party(self.party)]
        if extra_act_as:
            act_as.extend(extra_act_as)

        cid = contract_id

        if isinstance(cid, str):
            cid = ContractId(self._template_type, contract_id)

        res = await self.client.exercise(
            cid,
            choice,
            argument,
            act_as=act_as,
            read_as=act_as,
        )
        return to_jsonable(res)

    # =============================
    # MAIN METHODS
    # =============================

    async def create_property_async(
        self,
        registrar: str,
        owner: str,
        property_id: str,
        address: str,
        property_type: str,
        area: str,
        meta_json: str,
        price: str,
        currency: str,
        listed: bool = False,
    ):
        """
        Создает новый контракт RealEstate в леджере.

        Args:
            registrar: Party регистратора (подписант контракта).
            owner: Party начального владельца.
            property_id: Уникальный ID объекта недвижимости.
            address: Адрес объекта недвижимости.
            property_type: Тип объекта (например, "apartment", "house").
            area: Площадь в квадратных метрах (строка, будет преобразована в Decimal).
            meta_json: JSON строка с дополнительными метаданными.
            price: Начальная цена (строка, будет преобразована в Decimal).
            currency: Код валюты (например, "USD", "EUR").
            listed: Выставить на продажу сразу при создании (по умолчанию False).

        Returns:
            Dict с полями:
            - contractId: ID созданного контракта
            - payload: Данные контракта

        Raises:
            Exception: При ошибках создания контракта или валидации.
        """
        registrar_id = await self._resolve_party(self.client, registrar)
        owner_id = await self._resolve_party(self.client, owner)

        event = await self.client.create(
            "RealEstate:RealEstate",
            {
                "registrar": registrar_id,
                "owner": owner_id,
                "propertyId": property_id,
                "address": address,
                "propertyType": property_type,
                "area": area,
                "metaJson": meta_json,
                "status": "Active",
                "history": [],
                "listed": listed,
                "price": price,
                "currency": currency,
            },
            act_as=[Party(registrar_id)],
        )
        return to_jsonable(event)

    async def transfer_property_async(self, contract_id: str, new_owner: str):
        """
        Передает право собственности новому владельцу (choice Transfer).

        Args:
            contract_id: ID контракта RealEstate.
            new_owner: Party нового владельца.

        Returns:
            Результат выполнения choice (новый контракт с обновленным owner).

        Raises:
            Exception: Если контракт архивирован или вызов не авторизован.
        """
        return await self._exercise(contract_id, "Transfer", {"newOwner": new_owner})

    async def update_meta_async(self, contract_id: str, meta_json: str):
        """
        Обновляет метаданные объекта недвижимости (choice UpdateMeta).

        Args:
            contract_id: ID контракта RealEstate.
            meta_json: Новая JSON строка с метаданными.

        Returns:
            Результат выполнения choice (новый контракт с обновленными метаданными).

        Raises:
            Exception: Если контракт архивирован или вызов не авторизован.
        """
        return await self._exercise(contract_id, "UpdateMeta", {"newMetaJson": meta_json})

    async def archive_property_async(self, contract_id: str):
        """
        Архивирует контракт RealEstate (choice ArchiveProperty).

        Может быть выполнено только регистратором.

        Args:
            contract_id: ID контракта RealEstate.

        Returns:
            Результат выполнения choice (пустой объект).

        Raises:
            Exception: Если контракт уже архивирован или вызов не авторизован.
        """
        return await self._exercise(contract_id, "ArchiveProperty", {})

    async def list_properties_async(self):
        """
        Получает список всех активных контрактов RealEstate, видимых текущему party.

        Returns:
            List[Dict]: Список контрактов, каждый содержит:
            - contractId: ID контракта
            - payload: Данные контракта (все поля RealEstate)

        Raises:
            Exception: При ошибках запроса к леджеру.
        """
        result = []
        async for event in self.client.query("RealEstate:RealEstate"):
            if isinstance(event, CreateEvent):
                if self._template_type is None:
                    self._template_type = event.contract_id.value_type
                result.append({
                    "contractId": str(event.contract_id),
                    "payload": to_jsonable(event.payload),
                })
        return result

    async def mint_cash_async(self, issuer: str, owner: str, amount: str, currency: str):
        """
        Создает новый контракт Cash (демо-деньги для оплаты покупки).

        Args:
            issuer: Party эмитента (обычно продавец).
            owner: Party владельца денег (обычно покупатель).
            amount: Сумма (строка, будет преобразована в Decimal).
            currency: Код валюты (например, "USD", "EUR").

        Returns:
            Dict с полями:
            - contractId: ID созданного контракта Cash
            - payload: Данные контракта

        Raises:
            Exception: При ошибках создания контракта или валидации (amount > 0).
        """
        issuer_id = await self._resolve_party(self.client, issuer)
        owner_id = await self._resolve_party(self.client, owner)
        event = await self.client.create(
            "RealEstate:Cash",
            {
                "issuer": issuer_id,
                "owner": owner_id,
                "currency": currency,
                "amount": amount,
            },
            act_as=[Party(owner_id)],
        )
        return to_jsonable(event)

    async def list_cash_async(self):
        """
        Получает список всех активных контрактов Cash, видимых текущему party.

        Returns:
            List[Dict]: Список контрактов Cash, каждый содержит:
            - contractId: ID контракта
            - payload: Данные контракта (issuer, owner, amount, currency)

        Raises:
            Exception: При ошибках запроса к леджеру.
        """
        result = []
        async for event in self.client.query("RealEstate:Cash"):
            if isinstance(event, CreateEvent):
                result.append({
                    "contractId": str(event.contract_id),
                    "payload": to_jsonable(event.payload),
                })
        return result

    async def list_for_sale_async(self, contract_id: str, price: str, currency: str):
        """
        Выставляет объект недвижимости на продажу (choice ListForSale).

        Устанавливает флаг listed=True и обновляет цену и валюту.

        Args:
            contract_id: ID контракта RealEstate.
            price: Цена продажи (строка, будет преобразована в Decimal, должна быть > 0).
            currency: Код валюты (не может быть пустым).

        Returns:
            Результат выполнения choice (новый контракт с listed=True).

        Raises:
            Exception: Если контракт архивирован, цена <= 0, или currency пустая.
        """
        return await self._exercise(
            contract_id,
            "ListForSale",
            {"newPrice": price, "newCurrency": currency},
        )

    async def delist_property_async(self, contract_id: str):
        """
        Снимает объект недвижимости с продажи (choice Delist).

        Устанавливает флаг listed=False.

        Args:
            contract_id: ID контракта RealEstate.

        Returns:
            Результат выполнения choice (новый контракт с listed=False).

        Raises:
            Exception: Если контракт архивирован или вызов не авторизован.
        """
        return await self._exercise(contract_id, "Delist", {})

    async def buy_property_async(self, contract_id: str, price: str, currency: str, buyer: str, payment_cid: str, seller: str):
        """
        Покупает объект недвижимости (choice Buy - multi-controller).

        Требует подписи как продавца (owner), так и покупателя (buyer).
        Валидирует точное совпадение цены, валюты и платежного контракта.
        При успехе:
        1. Архивирует Cash контракт покупателя.
        2. Создает новый Cash контракт для продавца.
        3. Переносит собственность на покупателя.

        Args:
            contract_id: ID контракта RealEstate для покупки.
            price: Предлагаемая цена (должна совпадать с ценой в контракте).
            currency: Валюта (должна совпадать с валютой в контракте).
            buyer: Party покупателя.
            payment_cid: ID контракта Cash с точной суммой и валютой.
            seller: Party продавца (текущий owner).

        Returns:
            Результат выполнения choice (новый контракт с buyer как owner).

        Raises:
            Exception: Если:
            - контракт не выставлен на продажу (listed=False)
            - цена или валюта не совпадают
            - payment contract не принадлежит buyer
            - сумма в payment контракте не совпадает
            - вызов не авторизован обоими parties
        """
        buyer_id = await self._resolve_party(self.client, buyer)
        seller_id = await self._resolve_party(self.client, seller)
        return await self._exercise(
            contract_id,
            "Buy",
            {
                "offeredPrice": price,
                "offeredCurrency": currency,
                "buyer": buyer_id,
                "paymentCid": payment_cid,
            },
            extra_act_as=[Party(buyer_id), Party(seller_id)],
        )

    async def list_parties_async(self):
        """
        Получает список всех известных parties в леджере.

        Returns:
            List[Dict]: Список parties, каждый содержит:
            - id: Канонический ID party
            - displayName: Отображаемое имя party

        Raises:
            Exception: При ошибках запроса к леджеру.
        """
        infos = await self.client.list_known_parties()
        return [
            {"id": str(info.party), "displayName": info.display_name}
            for info in infos
        ]

    async def allocate_parties_async(self, hints: List[str]):
        """
        Создает новые parties в леджере (пропускает уже существующие).

        Проверяет существование каждого party перед созданием.
        Party считается существующим, если его ID начинается с "{hint}-"
        или displayName совпадает с hint.

        Args:
            hints: Список подсказок для создания parties (например, ["Buyer", "Seller"]).

        Returns:
            List[str]: Список канонических ID созданных parties.
            Пустой список, если все parties уже существовали.

        Raises:
            Exception: При ошибках создания parties в леджере.
        """
        infos = await self.client.list_known_parties()

        created = []
        for hint in hints:
            if any(str(info.party).startswith(f"{hint}-") or info.display_name == hint for info in infos):
                continue
            p = await self.client.allocate_party(identifier_hint=hint, display_name=hint)
            created.append(str(p.party))

        return to_jsonable(created)
