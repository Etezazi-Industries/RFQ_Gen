from .utils import with_db_conn
from typing import Dict, Tuple, Any


@with_db_conn()
def get_all_party_data(cursor) -> Dict[int, str]:
    query = "SELECT PartyPK, Name FROM Party ORDER BY Name ASC"
    cursor.execute(query)
    results = cursor.fetchall()
    return {int(party_pk): name for party_pk, name in results if name}


@with_db_conn()
def get_party_shortname_email(cursor, party_pk: int) -> Tuple[str, str]:
    query = "SELECT ShortName, Email FROM Party WHERE PartyPK = ?"
    cursor.execute(query, (party_pk,))
    results = cursor.fetchone()

    if len(results) == 2:
        return results[0], results[1]
    else:
        raise ValueError()


@with_db_conn()
def get_all_buyers_for_party(cursor, party_pk: int) -> Dict[int, str]:
    query = """
        SELECT p.Name, pb.BuyerFK
        FROM PartyBuyer pb
        JOIN Party p ON pb.BuyerFK = p.PartyPK
        WHERE pb.PartyFK = ?
        ORDER BY p.Name;
    """
    cursor.execute(query, (party_pk,))
    results = cursor.fetchall()

    if not results:
        raise ValueError(f"Database did not return any values for PartyPK: {party_pk}")

    return {buyer_fk: name for name, buyer_fk in results}


@with_db_conn()
def get_party_address(cursor, party_pk: int) -> Dict[str, Any]:
    query = """
        SELECT 
            a.AddressPK,
            a.Name,
            a.Address1,
            a.Address2,
            a.AddressAlt,
            a.City,
            a.ZipCode,
            s.Description AS State,
            c.Description AS Country
        FROM Address a
        LEFT JOIN State s ON a.StateFK = s.StatePK
        LEFT JOIN Country c ON a.CountryFK = c.CountryPK
        WHERE a.PartyFK = ?;
        """

    cursor.execute(query, (party_pk,))
    result = cursor.fetchone()

    if not result:
        raise ValueError(
            f"MT did not return any values for query:\n{query}\nPartyFK: {party_pk}"
        )

    address_details = {
        "address_pk": result[0],
        "name": result[1],
        "address1": result[2],
        "address2": result[3],
        "address_alt": result[4],
        "city": result[5],
        "zip_code": result[6],
        "state": result[7],  # No need to store it as a tuple
        "country": result[8],
    }

    return address_details
