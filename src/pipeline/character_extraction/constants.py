"""
Shared constants for character extraction.

This module contains common data structures used across the character extraction pipeline,
particularly for name normalization and alias detection.
"""

# Comprehensive nickname/variant mapping for alias detection.
# This map is bidirectional - if you look up a full name you get nicknames,
# if you look up a nickname you can find the full name.
# Some entries are explicitly bidirectional (e.g., kate <-> cathy) to ensure
# the relationship is captured regardless of which name is encountered first.
NICKNAME_MAP = {
    # Elizabeth variants
    'elizabeth': ['lizzy', 'liz', 'beth', 'eliza', 'betty', 'bess', 'bessie', 'lisa', 'ellie'],
    # William variants
    'william': ['will', 'bill', 'billy', 'willy', 'liam'],
    # Robert variants
    'robert': ['rob', 'bob', 'bobby', 'robbie', 'bert'],
    # Richard variants
    'richard': ['rick', 'dick', 'ricky', 'richie', 'rich'],
    # James variants
    'james': ['jim', 'jimmy', 'jamie', 'jem'],
    # Katherine/Catherine variants - CRITICAL: includes kate<->cathy bidirectional
    # These are all variants of the same root name and should be considered potential aliases
    'katherine': ['kate', 'kathy', 'katie', 'kitty', 'cathy', 'cat', 'kat', 'kay'],
    'catherine': ['kate', 'kathy', 'katie', 'kitty', 'cathy', 'cat', 'kat', 'kay'],
    'kate': ['cathy', 'kathy', 'katie', 'kitty', 'katherine', 'catherine', 'cat', 'kat'],
    'cathy': ['kate', 'kathy', 'katie', 'kitty', 'katherine', 'catherine', 'cat', 'kat'],
    # Margaret variants
    'margaret': ['maggie', 'meg', 'peggy', 'marge', 'madge', 'greta', 'maisie'],
    # Nicholas variants
    'nicholas': ['nick', 'nicky', 'nico', 'cole'],
    # Additional common names - male
    'alexander': ['alex', 'al', 'xander', 'sandy', 'lex'],
    'alexandra': ['alex', 'lexi', 'sandra', 'sandy', 'alexa'],
    'anthony': ['tony', 'ant'],
    'benjamin': ['ben', 'benny', 'benji'],
    'charles': ['charlie', 'chuck', 'chas'],
    'christopher': ['chris', 'kit', 'topher'],
    'daniel': ['dan', 'danny'],
    'david': ['dave', 'davy'],
    'edward': ['ed', 'eddie', 'ted', 'teddy', 'ned'],
    'francis': ['frank', 'frankie', 'fran'],
    'frederick': ['fred', 'freddy', 'fritz'],
    'george': ['georgie'],
    'gregory': ['greg', 'gregg'],
    'henry': ['hank', 'harry', 'hal'],
    'jacob': ['jake', 'jack'],
    'john': ['jack', 'johnny', 'jon'],
    'jonathan': ['jon', 'johnny', 'nathan'],
    'joseph': ['joe', 'joey', 'jo'],
    'joshua': ['josh'],
    'lawrence': ['larry', 'laurie'],
    'matthew': ['matt', 'matty'],
    'michael': ['mike', 'mikey', 'mick'],
    'nathaniel': ['nate', 'nathan', 'nat'],
    'patrick': ['pat', 'paddy'],
    'peter': ['pete', 'petey'],
    'philip': ['phil'],
    'raymond': ['ray'],
    'samuel': ['sam', 'sammy'],
    'stephen': ['steve', 'stevie'],
    'steven': ['steve', 'stevie'],
    'theodore': ['ted', 'teddy', 'theo'],
    'thomas': ['tom', 'tommy'],
    'timothy': ['tim', 'timmy'],
    'vincent': ['vince', 'vinny'],
    'walter': ['walt', 'wally'],
    # Female names
    'abigail': ['abby', 'gail'],
    'alice': ['allie', 'ally'],
    'amanda': ['mandy', 'manda'],
    'andrea': ['andy', 'andie'],
    'angela': ['angie'],
    'ann': ['annie', 'anna', 'anne', 'nan', 'nancy'],
    'anna': ['annie', 'ann', 'anne', 'nan', 'nancy'],
    'barbara': ['barb', 'barbie', 'babs'],
    'beatrice': ['bea', 'trixie'],
    'caroline': ['carrie', 'carol'],
    'charlotte': ['charlie', 'lottie', 'char'],
    'christina': ['chris', 'tina', 'christy'],
    'christine': ['chris', 'tina', 'christy'],
    'deborah': ['deb', 'debbie', 'debby'],
    'dorothy': ['dot', 'dottie', 'dolly'],
    'eleanor': ['ellie', 'ella', 'nell', 'nelly'],
    'emily': ['em', 'emma', 'emmy'],
    'eugenia': ['gene', 'genie'],
    'florence': ['flo', 'flossie'],
    'frances': ['fran', 'frannie', 'fanny'],
    'gabriella': ['gabi', 'gabby', 'ella'],
    'harriet': ['hattie', 'hatty'],
    'helen': ['nell', 'nellie', 'lena'],
    'henrietta': ['hettie', 'hetty', 'etta'],
    'jacqueline': ['jackie', 'jacqui'],
    'jane': ['janey', 'janie'],
    'janet': ['jan'],
    'jennifer': ['jen', 'jenny', 'jenn'],
    'jessica': ['jess', 'jessie'],
    'josephine': ['jo', 'josie'],
    'judith': ['judy', 'jude'],
    'julia': ['julie', 'jules'],
    'laura': ['laurie'],
    'lillian': ['lilly', 'lily', 'lil'],
    'louisa': ['lou', 'lulu'],
    'louise': ['lou', 'lulu'],
    'madeline': ['maddie', 'maddy', 'madeleine'],
    'mary': ['marie', 'molly', 'polly', 'mamie', 'may'],
    'matilda': ['mattie', 'tilda', 'tillie'],
    'nancy': ['nan'],
    'patricia': ['pat', 'patty', 'tricia', 'trish'],
    'penelope': ['penny'],
    'priscilla': ['prissy', 'cilla'],
    'rachel': ['ray'],
    'rebecca': ['becky', 'becca'],
    'rosalind': ['rosa', 'rose', 'roz'],
    'rosemary': ['rose', 'rosie'],
    'ruth': ['ruthie'],
    'samantha': ['sam', 'sammy'],
    'sarah': ['sally', 'sadie'],
    'sophia': ['sophie'],
    'stephanie': ['steph', 'stevie'],
    'susan': ['sue', 'susie', 'suzy'],
    'suzanne': ['sue', 'susie', 'suzy'],
    'sylvia': ['sylvie'],
    'teresa': ['terry', 'tess', 'tessa'],
    'theresa': ['terry', 'tess', 'tessa'],
    'veronica': ['ronnie', 'roni'],
    'victoria': ['vicky', 'vickie', 'tori'],
    'virginia': ['ginny', 'ginger'],
    'vivian': ['viv', 'vivi'],
}


def get_nickname_variants(name: str) -> set[str]:
    """
    Get all nickname variants for a given name.

    Args:
        name: A name to look up (case-insensitive)

    Returns:
        Set of all related name variants (including the original)
    """
    name_lower = name.lower()
    variants = {name_lower}

    # Direct lookup
    if name_lower in NICKNAME_MAP:
        variants.update(NICKNAME_MAP[name_lower])

    # Reverse lookup - find if this name is a nickname of something else
    for full_name, nicknames in NICKNAME_MAP.items():
        if name_lower in nicknames:
            variants.add(full_name)
            variants.update(nicknames)

    return variants


def are_potential_nicknames(name1: str, name2: str) -> bool:
    """
    Check if two names could be nickname variants of each other.

    Args:
        name1: First name
        name2: Second name

    Returns:
        True if the names could be related through nickname patterns
    """
    variants1 = get_nickname_variants(name1)
    name2_lower = name2.lower()
    return name2_lower in variants1
